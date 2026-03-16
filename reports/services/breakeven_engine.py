# reports/services/breakeven_engine.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db.models import Sum, Q
from django.db.models.functions import Coalesce


# =========================
#  Models / Fields (مطابقة لمشروعك)
# =========================
SALES_LINE_MODEL = "sales.SalesSummaryLine"        # موجود عندك :contentReference[oaicite:5]{index=5}
SALES_AMOUNT_FIELD = "line_total"                  # :contentReference[oaicite:6]{index=6}
SALES_QTY_FIELD = "quantity"                       # :contentReference[oaicite:7]{index=7}
SALES_PRODUCT_FK = "product"                       # :contentReference[oaicite:8]{index=8}

# الربط الصحيح للتاريخ عبر Period:
# SalesSummaryLine -> summary (SalesSummary) -> period (Period) -> start_date/end_date
SALES_PERIOD_START_FIELD = "summary__period__start_date"
SALES_PERIOD_END_FIELD = "summary__period__end_date"

# استهلاك المواد (SalesConsumption)
CONSUMPTION_MODEL = "sales.SalesConsumption"       # :contentReference[oaicite:9]{index=9}
# SalesConsumption -> summary (SalesConsumptionSummary) -> period (Period) -> start_date/end_date
CONSUMPTION_PERIOD_START_FIELD = "summary__period__start_date"
CONSUMPTION_PERIOD_END_FIELD = "summary__period__end_date"
# التكلفة الحقيقية موجودة باسم total_cost :contentReference[oaicite:10]{index=10}
CONSUMPTION_COST_FIELD = "total_cost"

# المصروفات (ExpenseLine)
EXPENSE_LINE_MODEL = "expenses.ExpenseLine"        # :contentReference[oaicite:11]{index=11}
EXPENSE_AMOUNT_FIELD = "amount"                    # :contentReference[oaicite:12]{index=12}
# ExpenseLine -> batch (ExpenseBatch) -> period (Period) -> start_date/end_date :contentReference[oaicite:13]{index=13}
EXPENSE_PERIOD_START_FIELD = "batch__period__start_date"
EXPENSE_PERIOD_END_FIELD = "batch__period__end_date"
# سلوك المصروف ثابت/متغير موجود في ExpenseCategory.behavior :contentReference[oaicite:14]{index=14}
EXPENSE_BEHAVIOR_FIELD = "item__category__behavior"
EXPENSE_BEHAVIOR_FIXED = "FIXED"
EXPENSE_BEHAVIOR_VARIABLE = "VARIABLE"


@dataclass
class BreakevenResult:
    sales: Decimal
    cogs_or_consumption: Decimal
    variable_expenses: Decimal
    fixed_expenses: Decimal
    contribution_margin: Decimal
    cm_ratio: Decimal
    breakeven_sales: Decimal
    profit: Decimal
    per_sku: List[Dict[str, Any]]
    variable_expense_rows: List[Dict[str, Any]]
    fixed_expense_rows: List[Dict[str, Any]]


def _d(v) -> Decimal:
    return v if isinstance(v, Decimal) else Decimal(str(v or 0))


def _overlap_q(start_field: str, end_field: str, date_from, date_to) -> Q:
    """
    فلترة بالفترات المتقاطعة:
    period.start_date <= date_to AND period.end_date >= date_from
    (وهذا أدق من start>=from & end<=to في التقارير الشهرية)
    """
    return Q(**{f"{start_field}__lte": date_to}) & Q(**{f"{end_field}__gte": date_from})


def calc_breakeven(
    date_from,
    date_to,
    allocate_fixed_method: str = "sales",  # sales | qty | cogs | cm
    include_per_sku: bool = True,
) -> BreakevenResult:
    """
    يحسب نقطة التعادل والربحية اعتماداً على:
    - SalesSummaryLine (مبيعات)
    - SalesConsumption.total_cost (تكلفة المواد المستهلكة)
    - ExpenseLine عبر ExpenseCategory.behavior (ثابت/متغير)
    """
    from django.apps import apps

    SalesLine = apps.get_model(*SALES_LINE_MODEL.split("."))
    Consumption = apps.get_model(*CONSUMPTION_MODEL.split("."))
    ExpenseLine = apps.get_model(*EXPENSE_LINE_MODEL.split("."))
    Product = SalesLine._meta.get_field(SALES_PRODUCT_FK).remote_field.model

    # -------------------------
    # 1) إجمالي المبيعات
    # -------------------------
    sales_qs = SalesLine.objects.all()

    # استبعاد السجلات التي ليس لها Period (لأن period عندك nullable) :contentReference[oaicite:15]{index=15}
    sales_qs = sales_qs.filter(summary__period__isnull=False)
    sales_qs = sales_qs.filter(_overlap_q(SALES_PERIOD_START_FIELD, SALES_PERIOD_END_FIELD, date_from, date_to))

    sales_totals = sales_qs.aggregate(
        sales=Coalesce(Sum(SALES_AMOUNT_FIELD), Decimal("0.0")),
        qty=Coalesce(Sum(SALES_QTY_FIELD), Decimal("0.0")),
    )
    total_sales = _d(sales_totals["sales"])
    total_sales_qty = _d(sales_totals["qty"])

    # -------------------------
    # 2) تكلفة الاستهلاك / COGS (من SalesConsumption.total_cost)
    # -------------------------
    cons_qs = Consumption.objects.all()
    cons_qs = cons_qs.filter(summary__period__isnull=False)
    cons_qs = cons_qs.filter(_overlap_q(CONSUMPTION_PERIOD_START_FIELD, CONSUMPTION_PERIOD_END_FIELD, date_from, date_to))

    consumption_totals = cons_qs.aggregate(
        cons=Coalesce(Sum(CONSUMPTION_COST_FIELD), Decimal("0.0")),
    )
    total_consumption_cost = _d(consumption_totals["cons"])

    # -------------------------
    # 3) المصروفات (Fixed/Variable) عبر ExpenseCategory.behavior
    # -------------------------
    exp_qs = ExpenseLine.objects.all()
    exp_qs = exp_qs.filter(batch__period__isnull=False)
    exp_qs = exp_qs.filter(_overlap_q(EXPENSE_PERIOD_START_FIELD, EXPENSE_PERIOD_END_FIELD, date_from, date_to))

    fixed = exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: EXPENSE_BEHAVIOR_FIXED}).aggregate(
        total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0"))
    )["total"]
    variable = exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: EXPENSE_BEHAVIOR_VARIABLE}).aggregate(
        total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0"))
    )["total"]

    fixed = _d(fixed)
    variable = _d(variable)

    # -------------------------
    # 3.b) ✅ تفصيل المصروفات حسب البنود
    # -------------------------
    def _expense_rows(behavior_code: str):
        return list(
            exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: behavior_code})
            .values(
                "item__code",
                "item__name",
                "item__category__name",
            )
            .annotate(total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0")))
            .order_by("-total")
        )

    variable_rows = _expense_rows(EXPENSE_BEHAVIOR_VARIABLE)
    fixed_rows = _expense_rows(EXPENSE_BEHAVIOR_FIXED)

    # -------------------------
    # 4) حسابات نقطة التعادل
    # -------------------------
    contribution_margin = total_sales - (total_consumption_cost + variable)

    cm_ratio = Decimal("0.0")
    if total_sales > 0:
        cm_ratio = contribution_margin / total_sales

    breakeven_sales = Decimal("0.0")
    if cm_ratio > 0:
        breakeven_sales = fixed / cm_ratio

    profit = contribution_margin - fixed

    # -------------------------
    # 5) تحليل حسب الصنف (Product)
    # -------------------------
    per_sku: List[Dict[str, Any]] = []
    if include_per_sku:
        # لازم نحولها List لأننا سنستخدمها مرتين (مرة IDs ومرة loop)
        sku_rows = list(
            sales_qs.values(SALES_PRODUCT_FK)
            .annotate(
                sales=Coalesce(Sum(SALES_AMOUNT_FIELD), Decimal("0.0")),
                qty=Coalesce(Sum(SALES_QTY_FIELD), Decimal("0.0")),
            )
        )

        # جلب بيانات المنتجات مرة واحدة (code/name)
        product_ids = [row[SALES_PRODUCT_FK] for row in sku_rows if row.get(SALES_PRODUCT_FK) is not None]
        products = Product.objects.filter(id__in=product_ids).values("id", "code", "name")
        product_map = {
            p["id"]: {
                "code": p.get("code", ""),
                "name": p.get("name", ""),
            }
            for p in products
        }

        # تكلفة الاستهلاك لكل منتج نهائي
        cons_by_sku = list(
            cons_qs.values("product")
            .annotate(cons=Coalesce(Sum(CONSUMPTION_COST_FIELD), Decimal("0.0")))
        )
        cons_map = {row["product"]: _d(row["cons"]) for row in cons_by_sku}

        totals_basis = {
            "sales": total_sales,
            "qty": total_sales_qty,
            "cogs": total_consumption_cost,
            "cm": contribution_margin if contribution_margin > 0 else Decimal("0.0"),
        }
        denom = totals_basis.get(allocate_fixed_method, total_sales) or Decimal("0.0")

        for row in sku_rows:
            pid = row[SALES_PRODUCT_FK]
            sku_sales = _d(row["sales"])
            sku_qty = _d(row["qty"])
            sku_cons = cons_map.get(pid, Decimal("0.0"))

            sku_variable = Decimal("0.0")
            sku_cm = sku_sales - (sku_cons + sku_variable)

            basis_val = {
                "sales": sku_sales,
                "qty": sku_qty,
                "cogs": sku_cons,
                "cm": sku_cm if sku_cm > 0 else Decimal("0.0"),
            }.get(allocate_fixed_method, sku_sales)

            sku_fixed_alloc = Decimal("0.0")
            if denom > 0:
                sku_fixed_alloc = fixed * (basis_val / denom)

            sku_profit = sku_cm - sku_fixed_alloc

            prod = product_map.get(pid, {})

            per_sku.append({
                "product_id": pid,
                "product_code": prod.get("code", ""),
                "product_name": prod.get("name", ""),
                "sales": sku_sales,
                "qty": sku_qty,
                "consumption_cost": sku_cons,
                "contribution_margin": sku_cm,
                "fixed_allocated": sku_fixed_alloc,
                "profit": sku_profit,
            })

        # ترتيب: الأكثر ربحية
        per_sku.sort(key=lambda x: x["profit"], reverse=True)


    return BreakevenResult(
        sales=total_sales,
        cogs_or_consumption=total_consumption_cost,
        variable_expenses=variable,
        fixed_expenses=fixed,
        contribution_margin=contribution_margin,
        cm_ratio=cm_ratio,
        breakeven_sales=breakeven_sales,
        profit=profit,
        per_sku=per_sku,
        variable_expense_rows=variable_rows,
        fixed_expense_rows=fixed_rows,
    )
