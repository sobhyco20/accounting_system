# reports/services/breakeven_simulator_engine_v2.py
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Any, List, Optional

from django.db.models import Sum
from django.db.models.functions import Coalesce


SALES_LINE_MODEL = "sales.SalesSummaryLine"
SALES_AMOUNT_FIELD = "line_total"
SALES_QTY_FIELD = "quantity"
SALES_PRODUCT_FK = "product"

CONSUMPTION_MODEL = "sales.SalesConsumption"
CONSUMPTION_COST_FIELD = "total_cost"

EXPENSE_LINE_MODEL = "expenses.ExpenseLine"
EXPENSE_AMOUNT_FIELD = "amount"
EXPENSE_BEHAVIOR_FIELD = "item__category__behavior"
EXPENSE_BEHAVIOR_FIXED = "FIXED"
EXPENSE_BEHAVIOR_VARIABLE = "VARIABLE"


@dataclass
class BreakevenSimulatorResult:
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


def calc_breakeven_simulator_by_period(
    period,
    allocate_fixed_method: str = "sales",  # sales | qty | cogs | cm
    include_per_sku: bool = True,
) -> BreakevenSimulatorResult:
    """
    ✅ يعتمد على period مباشرة:
    - SalesSummaryLine.summary__period = period
    - SalesConsumption.summary__period = period
    - ExpenseLine.batch__period = period
    """
    from django.apps import apps

    SalesLine = apps.get_model(*SALES_LINE_MODEL.split("."))
    Consumption = apps.get_model(*CONSUMPTION_MODEL.split("."))
    ExpenseLine = apps.get_model(*EXPENSE_LINE_MODEL.split("."))

    Product = SalesLine._meta.get_field(SALES_PRODUCT_FK).remote_field.model

    # 1) Sales (بالـ period مباشرة)
    sales_qs = SalesLine.objects.filter(summary__period=period)

    sales_totals = sales_qs.aggregate(
        sales=Coalesce(Sum(SALES_AMOUNT_FIELD), Decimal("0.0")),
        qty=Coalesce(Sum(SALES_QTY_FIELD), Decimal("0.0")),
    )
    total_sales = _d(sales_totals["sales"])
    total_sales_qty = _d(sales_totals["qty"])

    # 2) Consumption (بالـ period مباشرة)
    cons_qs = Consumption.objects.filter(summary__period=period)
    cons_totals = cons_qs.aggregate(
        cons=Coalesce(Sum(CONSUMPTION_COST_FIELD), Decimal("0.0"))
    )
    total_consumption_cost = _d(cons_totals["cons"])

    # 3) Expenses (بالـ period مباشرة)
    exp_qs = ExpenseLine.objects.filter(batch__period=period)

    fixed = _d(
        exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: EXPENSE_BEHAVIOR_FIXED})
        .aggregate(total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0")))["total"]
    )

    variable = _d(
        exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: EXPENSE_BEHAVIOR_VARIABLE})
        .aggregate(total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0")))["total"]
    )

    def _expense_rows(behavior_code: str) -> List[Dict[str, Any]]:
        return list(
            exp_qs.filter(**{EXPENSE_BEHAVIOR_FIELD: behavior_code})
            .values("item__code", "item__name", "item__category__name")
            .annotate(total=Coalesce(Sum(EXPENSE_AMOUNT_FIELD), Decimal("0.0")))
            .order_by("-total")
        )

    variable_rows = _expense_rows(EXPENSE_BEHAVIOR_VARIABLE)
    fixed_rows = _expense_rows(EXPENSE_BEHAVIOR_FIXED)

    # 4) BEP math
    contribution_margin = total_sales - (total_consumption_cost + variable)

    cm_ratio = Decimal("0.0")
    if total_sales > 0:
        cm_ratio = contribution_margin / total_sales

    breakeven_sales = Decimal("0.0")
    if cm_ratio > 0:
        breakeven_sales = fixed / cm_ratio

    profit = contribution_margin - fixed

    # 5) Per SKU
    per_sku: List[Dict[str, Any]] = []

    if include_per_sku:
        sku_rows = list(
            sales_qs.values(SALES_PRODUCT_FK)
            .annotate(
                sales=Coalesce(Sum(SALES_AMOUNT_FIELD), Decimal("0.0")),
                qty=Coalesce(Sum(SALES_QTY_FIELD), Decimal("0.0")),
            )
        )

        product_ids = [row[SALES_PRODUCT_FK] for row in sku_rows if row.get(SALES_PRODUCT_FK)]
        products = Product.objects.filter(id__in=product_ids).values("id", "code", "name")
        product_map = {p["id"]: {"code": p.get("code", ""), "name": p.get("name", "")} for p in products}

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

            sku_cm = sku_sales - sku_cons

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

            unit_price = (sku_sales / sku_qty) if sku_qty > 0 else Decimal("0.0")
            unit_cost = (sku_cons / sku_qty) if sku_qty > 0 else Decimal("0.0")

            prod = product_map.get(pid, {})
            per_sku.append({
                "product_id": pid,
                "product_code": prod.get("code", ""),
                "product_name": prod.get("name", ""),

                "qty": sku_qty,
                "sales": sku_sales,
                "consumption_cost": sku_cons,

                "unit_price": unit_price,
                "unit_cost": unit_cost,

                "contribution_margin": sku_cm,
                "fixed_allocated": sku_fixed_alloc,
                "profit": sku_profit,
            })

        per_sku.sort(key=lambda x: x["profit"], reverse=True)

    return BreakevenSimulatorResult(
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
