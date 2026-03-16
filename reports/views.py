# reports/views.py
from __future__ import annotations

from collections import OrderedDict
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO

from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from costing.models import BOMItem, Product, RawMaterial, round3
from expenses.models import Period, ExpenseBatch, ExpenseLine
from sales.models import SalesConsumption, get_quantity_sold, SalesSummaryLine, SalesSummary

# xhtml2pdf (قديم) — نتركه اختياري
from xhtml2pdf import pisa

# playwright (PDF عربي ممتاز)
# playwright (PDF عربي ممتاز)
try:
    from playwright.sync_api import sync_playwright
except Exception:
    sync_playwright = None



# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
MONEY = Decimal("0.01")
def money(x):
    return (x or Decimal("0")).quantize(MONEY, rounding=ROUND_HALF_UP)


def get_default_period():
    """
    اختيار فترة افتراضية:
    - أولاً: آخر فترة غير مغلقة is_closed=False (إن وجدت)
    - وإلا: آخر فترة حسب start_date
    """
    current = Period.objects.filter(is_closed=False).order_by("-start_date").first()
    if current:
        return current
    return Period.objects.order_by("-start_date").first()


def html_to_pdf_response_xhtml2pdf(html_string: str, filename: str) -> HttpResponse:
    """
    PDF قديم (xhtml2pdf) — غالباً لا يدعم العربية بشكل سليم.
    """
    result = BytesIO()
    pdf = pisa.CreatePDF(src=html_string, dest=result, encoding="UTF-8")

    if pdf.err:
        return HttpResponse("تعذر إنشاء ملف PDF.", status=500)

    response = HttpResponse(result.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def html_to_pdf_playwright(request, template_name: str, context: dict, filename: str) -> HttpResponse:
    if sync_playwright is None:
        return HttpResponse(
            "Playwright غير مثبت داخل نفس البيئة.\n"
            "نفّذ:\n"
            "python -m pip install playwright\n"
            "python -m playwright install chromium",
            status=500,
            content_type="text/plain; charset=utf-8",
        )

    template = get_template(template_name)
    html_string = template.render({**context, "request": request})

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_string, wait_until="networkidle")
        pdf_bytes = page.pdf(
            format="A4",
            print_background=True,
            margin={"top": "12mm", "right": "10mm", "bottom": "12mm", "left": "10mm"},
        )
        browser.close()

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



# ─────────────────────────────
# الصفحة الموحدة للتقارير
# ─────────────────────────────
def reports_home(request):
    return render(request, "reports/reports_home.html")


# ─────────────────────────────
# 1) تقرير تجميعي لاستهلاك المواد الخام
# ─────────────────────────────
def raw_material_consumption_summary(request):
    period_id = request.GET.get("period")
    periods = Period.objects.all().order_by("start_date")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    qs = SalesConsumption.objects.select_related("summary__period", "raw_material")
    if current_period:
        qs = qs.filter(summary__period=current_period)

    base_rows = (
        qs.values(
            "raw_material_id",
            "raw_material__sku",
            "raw_material__name",
            "raw_material__ingredient_unit__name",
        )
        .annotate(
            total_qty=Sum("quantity_consumed"),
            total_cost=Sum("total_cost"),
            total_orders=Sum("quantity_sold"),
        )
        .order_by("raw_material__name")
    )

    rows = []
    grand_total_cost = Decimal("0")

    for r in base_rows:
        total_qty = r["total_qty"] or Decimal("0")
        total_cost = r["total_cost"] or Decimal("0")
        total_orders = r["total_orders"] or Decimal("0")

        grand_total_cost += total_cost

        if total_orders:
            per_order_qty = total_qty / total_orders
            cost_per_order = total_cost / total_orders
        else:
            per_order_qty = None
            cost_per_order = None

        rows.append({
            "raw_material_id": r["raw_material_id"],
            "sku": r["raw_material__sku"],
            "name": r["raw_material__name"],
            "unit_name": r["raw_material__ingredient_unit__name"],
            "total_qty": total_qty,
            "total_cost": total_cost,
            "total_orders": total_orders,
            "per_order_qty": per_order_qty,
            "cost_per_order": cost_per_order,
        })

    context = {
        "periods": periods,
        "current_period": current_period,
        "rows": rows,
        "grand_total_cost": grand_total_cost,
    }
    return render(request, "reports/raw_material_consumption_summary.html", context)


# ─────────────────────────────
# 2) تقرير تفصيلي لاستهلاك المواد الخام
# ─────────────────────────────
def raw_material_consumption_detail(request):
    period_id = request.GET.get("period")
    periods = Period.objects.all().order_by("start_date")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    qs = SalesConsumption.objects.select_related(
        "summary__period", "product", "raw_material", "source_product"
    )
    if current_period:
        qs = qs.filter(summary__period=current_period)

    products_map = OrderedDict()
    grand_total_cost = Decimal("0")

    for line in qs.order_by("product__name", "level", "raw_material__name"):
        pid = line.product_id
        if pid not in products_map:
            products_map[pid] = {
                "product": line.product,
                "lines": [],
                "quantity_sold": Decimal("0"),
                "total_cost": Decimal("0"),
            }

        line_orders_sold = line.quantity_sold or Decimal("0")
        line_cost = line.total_cost or Decimal("0")

        per_order_qty = None
        cost_per_order = None
        if line_orders_sold:
            per_order_qty = (line.quantity_consumed or Decimal("0")) / line_orders_sold
            cost_per_order = line_cost / line_orders_sold

        products_map[pid]["lines"].append({
            "line": line,
            "orders_sold": line_orders_sold,
            "per_order_qty": per_order_qty,
            "cost_per_order": cost_per_order,
        })

        products_map[pid]["quantity_sold"] += line_orders_sold
        products_map[pid]["total_cost"] += line_cost
        grand_total_cost += line_cost

    for _, data in products_map.items():
        data["cost_per_order"] = (data["total_cost"] / data["quantity_sold"]) if data["quantity_sold"] > 0 else None

    context = {
        "periods": periods,
        "current_period": current_period,
        "products_data": products_map.values(),
        "grand_total_cost": grand_total_cost,
    }
    return render(request, "reports/raw_material_consumption_detail.html", context)


# ─────────────────────────────
# تقرير: مادة خام → في أي منتجات دخلت
# ─────────────────────────────
def raw_material_usage_by_product(request):
    period_id = request.GET.get("period")
    raw_material_id = request.GET.get("raw_material")

    periods = Period.objects.all().order_by("start_date")
    materials = RawMaterial.objects.all().order_by("name")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    qs = SalesConsumption.objects.select_related("summary__period", "product", "raw_material")
    if current_period:
        qs = qs.filter(summary__period=current_period)

    selected_material = None
    if raw_material_id:
        qs = qs.filter(raw_material_id=raw_material_id)
        selected_material = RawMaterial.objects.filter(id=raw_material_id).first()

    rows = []
    if selected_material:
        agg = (
            qs.values("product_id", "product__code", "product__name")
            .annotate(
                total_qty_sold=Sum("quantity_sold"),
                total_qty_consumed=Sum("quantity_consumed"),
                total_cost=Sum("total_cost"),
            )
            .order_by("product__name")
        )

        for r in agg:
            product_id = r["product_id"]

            bom_item = (
                BOMItem.objects.filter(
                    bom__product_id=product_id,
                    raw_material_id=selected_material.id,
                    bom__is_active=True,
                )
                .select_related("raw_material", "bom__product")
                .first()
            )

            per_order_qty = None
            per_order_unit = None
            if bom_item:
                per_order_qty = bom_item.quantity
                if bom_item.raw_material.ingredient_unit:
                    per_order_unit = bom_item.raw_material.ingredient_unit
                elif bom_item.raw_material.storage_unit:
                    per_order_unit = bom_item.raw_material.storage_unit

            rows.append({
                "product_code": r["product__code"],
                "product_name": r["product__name"],
                "total_qty_sold": r["total_qty_sold"] or Decimal("0"),
                "total_qty_consumed": r["total_qty_consumed"] or Decimal("0"),
                "total_cost": r["total_cost"] or Decimal("0"),
                "per_order_qty": per_order_qty,
                "per_order_unit": per_order_unit,
            })

    context = {
        "periods": periods,
        "current_period": current_period,
        "materials": materials,
        "selected_material": selected_material,
        "rows": rows,
    }
    return render(request, "reports/raw_material_usage_by_product.html", context)


# ───────────────────────────────────────────────
# BOM Tree Helpers
# ───────────────────────────────────────────────
def _product_label(p: Product) -> str:
    return f"{p.code} - {p.name}"


def _raw_label(rm: RawMaterial) -> str:
    return f"{rm.sku} - {rm.name}" if rm.sku else rm.name


def _collect_bom_tree(product, multiplier, level, parent_obj, lines, final_raw_totals, period, root_sold_qty):
    bom = product.get_active_bom()
    if not bom:
        return

    parent_label = _product_label(parent_obj) if isinstance(parent_obj, Product) else _raw_label(parent_obj)

    for item in bom.items.all():
        base_qty = item.quantity or Decimal("0")
        qty_total = base_qty * multiplier

        per_order_qty = (qty_total / root_sold_qty) if (root_sold_qty and root_sold_qty > 0) else None

        if item.component_product:
            semi = item.component_product
            semi_bom = semi.get_active_bom()

            unit_cost = None
            if semi_bom:
                unit_cost = semi_bom.unit_cost_final or semi_bom.unit_cost

            total_cost = (unit_cost * qty_total) if unit_cost is not None else None

            lines.append({
                "type": "manufactured",
                "level": level,
                "product": semi,
                "code": semi.code,
                "name": semi.name,
                "parent": parent_label,
                "qty": qty_total,
                "per_order_qty": per_order_qty,
                "unit_cost": unit_cost,
                "total_cost": total_cost,
            })

            batch_qty = (semi_bom.batch_output_quantity or Decimal("1")) if semi_bom else Decimal("1")
            semi_units_needed = qty_total / batch_qty

            _collect_bom_tree(
                product=semi,
                multiplier=semi_units_needed,
                level=level + 1,
                parent_obj=semi,
                lines=lines,
                final_raw_totals=final_raw_totals,
                period=period,
                root_sold_qty=root_sold_qty,
            )

        elif item.raw_material:
            rm = item.raw_material
            unit_cost = rm.get_cost_per_ingredient_unit(period=period)
            total_cost = (unit_cost * qty_total) if unit_cost is not None else None

            lines.append({
                "type": "raw",
                "level": level,
                "raw_material": rm,
                "code": rm.sku,
                "name": rm.name,
                "parent": parent_label,
                "qty": qty_total,
                "per_order_qty": per_order_qty,
                "unit_cost": unit_cost,
                "total_cost": total_cost,
            })

            if rm.id not in final_raw_totals:
                final_raw_totals[rm.id] = {"raw_material": rm, "total_qty": Decimal("0"), "total_cost": Decimal("0")}

            final_raw_totals[rm.id]["total_qty"] += qty_total
            if total_cost is not None:
                final_raw_totals[rm.id]["total_cost"] += total_cost


def raw_material_consumption_with_manufactured_detail(request):
    period_id = request.GET.get("period")
    periods = Period.objects.all().order_by("start_date")
    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    products_data = []
    grand_total_cost = Decimal("0")

    if current_period:
        for product in Product.objects.filter(is_sellable=True).order_by("name"):
            sold_qty = get_quantity_sold(product, current_period)
            if sold_qty <= 0:
                continue

            lines = []
            final_raw_totals = {}
            product_total_cost = Decimal("0")

            _collect_bom_tree(
                product=product,
                multiplier=sold_qty,
                level=1,
                parent_obj=product,
                lines=lines,
                final_raw_totals=final_raw_totals,
                period=current_period,
                root_sold_qty=sold_qty,
            )

            for row in lines:
                if row.get("type") == "raw" and row.get("total_cost") is not None:
                    product_total_cost += row["total_cost"]

            grand_total_cost += product_total_cost

            products_data.append({
                "product": product,
                "sold_qty": sold_qty,
                "lines": lines,
                "final_raw_totals": final_raw_totals,
                "product_total_cost": product_total_cost,
            })

    context = {"periods": periods, "current_period": current_period, "products_data": products_data, "grand_total_cost": grand_total_cost}
    return render(request, "reports/raw_material_consumption_with_manufactured_detail.html", context)


def build_product_cost_report(product, period, qty: Decimal):
    lines = []
    final_raw_totals = OrderedDict()
    manufactured_total_cost = Decimal("0")
    product_total_cost = Decimal("0")
    level1_total_cost = Decimal("0")
    level2_total_cost = Decimal("0")

    level1_raw_lines = []
    level1_manufactured_lines = []
    level2_lines = []

    _collect_bom_tree(
        product=product,
        multiplier=qty,
        level=1,
        parent_obj=product,
        lines=lines,
        final_raw_totals=final_raw_totals,
        period=period,
        root_sold_qty=qty,
    )

    for row in lines:
        level = row.get("level")
        row_type = row.get("type")
        total_cost = row.get("total_cost")

        if level == 1:
            (level1_manufactured_lines if row_type == "manufactured" else level1_raw_lines).append(row)
            if row_type == "raw" and total_cost is not None:
                level1_total_cost += total_cost

        elif level and level >= 2:
            level2_lines.append(row)
            if row_type == "raw" and total_cost is not None:
                level2_total_cost += total_cost

        if row_type == "raw" and total_cost is not None:
            product_total_cost += total_cost

        # ✅ اجمالي النصف مصنع للمستوى الأول
        if row_type == "manufactured" and total_cost is not None:
            manufactured_total_cost += total_cost

    level1_lines = level1_raw_lines + level1_manufactured_lines

    # ✅ تجميع المستوى الثاني حسب المصدر/المنتج الأعلى
    level2_groups_map = OrderedDict()

    for row in level2_lines:
        parent = row.get("parent") or "بدون مصدر"

        if parent not in level2_groups_map:
            level2_groups_map[parent] = {
                "parent": parent,
                "lines": [],
                "total_cost": Decimal("0"),  # مواد خام فقط داخل هذه المجموعة
            }

        level2_groups_map[parent]["lines"].append(row)

        if row.get("type") == "raw" and row.get("total_cost") is not None:
            level2_groups_map[parent]["total_cost"] += row["total_cost"]

    level2_groups = list(level2_groups_map.values())

    return {
        "product": product,
        "qty": qty,
        "final_raw_totals": final_raw_totals,
        "level1_lines": level1_lines,
        "level2_lines": level2_lines,
        "level2_groups": level2_groups,   
        "level1_total_cost": level1_total_cost,
        "level2_total_cost": level2_total_cost,
        "product_total_cost": product_total_cost,
        "manufactured_total_cost": manufactured_total_cost,
    }

def product_cost_breakdown(request):
    period_id = request.GET.get("period")
    product_id = request.GET.get("product")
    qty_param = request.GET.get("qty") or "1"

    periods = Period.objects.all().order_by("start_date")
    products = Product.objects.filter(is_sellable=True).order_by("name")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()
    selected_product = Product.objects.filter(id=product_id).first() if product_id else None

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    report_data = build_product_cost_report(selected_product, current_period, qty) if (current_period and selected_product) else None

    context = {
        "periods": periods,
        "products": products,
        "current_period": current_period,
        "selected_product": selected_product,
        "qty": qty,
        "report": report_data,
        "title": "تقرير تكلفة المنتج (تفكيك المكونات)",
    }
    return render(request, "reports/product_cost_breakdown.html", context)


# ✅ PDF (Playwright) — منتج واحد
def product_cost_breakdown_pdf(request):
    period_id = request.GET.get("period")
    product_id = request.GET.get("product")
    qty_param = request.GET.get("qty") or "1"

    if not (period_id and product_id):
        return HttpResponse("يجب اختيار الفترة والمنتج أولاً", status=400)

    period = Period.objects.filter(id=period_id).first()
    product = Product.objects.filter(id=product_id).first()
    if not (period and product):
        return HttpResponse("فترة أو منتج غير صحيح", status=404)

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    report = build_product_cost_report(product, period, qty)
    filename = f"product_cost_{product.code}.pdf"

    return html_to_pdf_playwright(
        request=request,
        template_name="reports/product_cost_breakdown_pdf.html",
        context={"current_period": period, "reports": [report], "title": "تقرير تكلفة المنتج"},
        filename=filename,
    )


# ✅ PDF (Playwright) — كل المنتجات
def product_cost_breakdown_all_pdf(request):
    period_id = request.GET.get("period")
    qty_param = request.GET.get("qty") or "1"

    if not period_id:
        return HttpResponse("يجب اختيار الفترة أولاً", status=400)

    period = Period.objects.filter(id=period_id).first()
    if not period:
        return HttpResponse("فترة غير صحيحة", status=404)

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    products = Product.objects.filter(is_sellable=True).order_by("name")
    reports = [build_product_cost_report(p, period, qty) for p in products]
    filename = f"products_cost_{period.id}.pdf"

    return html_to_pdf_playwright(
        request=request,
        template_name="reports/product_cost_breakdown_pdf.html",
        context={"current_period": period, "reports": reports, "title": "تقرير تكلفة المنتجات"},
        filename=filename,
    )


def product_cost_flat(request):
    period_id = request.GET.get("period")
    product_id = request.GET.get("product")
    qty_param = request.GET.get("qty") or "1"

    periods = Period.objects.all().order_by("start_date")
    products = Product.objects.filter(is_sellable=True).order_by("name")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()
    selected_product = Product.objects.filter(id=product_id).first() if product_id else None

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    components = []
    total_cost = Decimal("0")

    if current_period and selected_product:
        report = build_product_cost_report(selected_product, current_period, qty)
        all_rows = list(report["level1_lines"]) + list(report["level2_lines"])

        for r in all_rows:
            row_type = r.get("type")
            unit_cost = r.get("unit_cost")
            total_row_cost = r.get("total_cost") or Decimal("0")

            big_unit_name = ""
            small_unit_name = ""

            raw_obj = r.get("raw_material")
            prod_obj = r.get("product")

            if raw_obj:
                storage_unit = getattr(raw_obj, "storage_unit", None)
                ingredient_unit = getattr(raw_obj, "ingredient_unit", None)
                if storage_unit:
                    big_unit_name = getattr(storage_unit, "name", "") or ""
                if ingredient_unit:
                    small_unit_name = getattr(ingredient_unit, "name", "") or ""
                if not small_unit_name:
                    small_unit_name = big_unit_name

            elif prod_obj:
                selling_unit = getattr(prod_obj, "selling_unit", None)
                production_unit = getattr(prod_obj, "production_unit", None)
                if selling_unit:
                    big_unit_name = getattr(selling_unit, "name", "") or ""
                if production_unit:
                    small_unit_name = getattr(production_unit, "name", "") or ""
                if not small_unit_name:
                    small_unit_name = big_unit_name

            components.append({
                "type": row_type,
                "code": r.get("code"),
                "name": r.get("name"),
                "big_unit_cost": unit_cost,
                "big_unit_name": big_unit_name,
                "recipe_qty": r.get("qty"),
                "small_unit_name": small_unit_name,
                "total_cost": total_row_cost,
            })

        product_total_cost = report["product_total_cost"] or Decimal("0")
        product_unit_cost = (product_total_cost / qty) if qty else None
        selling_unit = getattr(selected_product, "selling_unit", None)
        big_unit_name = getattr(selling_unit, "name", "") if selling_unit else ""

        components.append({
            "type": "product",
            "code": selected_product.code,
            "name": selected_product.name,
            "big_unit_cost": product_unit_cost,
            "big_unit_name": big_unit_name,
            "recipe_qty": qty,
            "small_unit_name": "",
            "total_cost": product_total_cost,
        })

        total_cost = product_total_cost

    context = {"periods": periods, "products": products, "current_period": current_period, "selected_product": selected_product,
               "qty": qty, "components": components, "total_cost": total_cost, "title": "تقرير تكلفة المنتج (Flat)"}
    return render(request, "reports/product_cost_flat.html", context)


def _enrich_row_with_big_unit(row, period):
    big_unit_price = None
    big_unit_name = ""
    big_unit_size = ""
    big_unit_qty = None
    small_unit_name = ""

    raw_obj = row.get("raw_material")
    prod_obj = row.get("product")

    if raw_obj:
        storage_unit = getattr(raw_obj, "storage_unit", None)
        ingredient_unit = getattr(raw_obj, "ingredient_unit", None)
        factor = getattr(raw_obj, "storage_to_ingredient_factor", None)

        if storage_unit:
            big_unit_name = getattr(storage_unit, "name", "") or ""
        if ingredient_unit:
            small_unit_name = getattr(ingredient_unit, "name", "") or ""

        if not small_unit_name:
            small_unit_name = big_unit_name

        if factor:
            big_unit_qty = factor
            big_unit_size = f"{factor} {small_unit_name}"

        cost_small = raw_obj.get_cost_from_purchases(period=period)
        if cost_small is None:
            cost_small = raw_obj.get_cost_per_ingredient_unit(period=None)

        if cost_small is not None:
            big_unit_price = round3(cost_small * Decimal(str(factor))) if factor else round3(cost_small)

        if big_unit_price is None:
            purchase_price = getattr(raw_obj, "purchase_price_per_storage_unit", None)
            if purchase_price:
                big_unit_price = round3(purchase_price)

    elif prod_obj:
        selling_unit = getattr(prod_obj, "selling_unit", None)
        if selling_unit:
            big_unit_name = getattr(selling_unit, "name", "") or ""

        small_unit_name = big_unit_name

        if big_unit_name:
            big_unit_qty = Decimal("1")
            big_unit_size = f"1 {big_unit_name}"

        if hasattr(prod_obj, "compute_unit_cost"):
            unit_cost = prod_obj.compute_unit_cost(period=period)
            if unit_cost is not None:
                big_unit_price = round3(unit_cost)

    new_row = dict(row)
    new_row.update({
        "big_unit_price": big_unit_price,
        "big_unit_name": big_unit_name,
        "big_unit_size": big_unit_size,
        "big_unit_qty": big_unit_qty,
        "small_unit_name": small_unit_name,
    })
    return new_row


def product_cost_with_big_units(request):
    period_id = request.GET.get("period")
    product_id = request.GET.get("product")
    qty_param = request.GET.get("qty") or "1"

    periods = Period.objects.all().order_by("start_date")
    products = Product.objects.filter(is_sellable=True).order_by("name")

    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()
    selected_product = Product.objects.filter(id=product_id).first() if product_id else None

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    level1_rows = []
    level2_rows = []
    level1_total_cost = Decimal("0")
    level2_total_cost = Decimal("0")
    product_total_cost = None

    if current_period and selected_product:
        base_report = build_product_cost_report(selected_product, current_period, qty)
        level1_rows = [_enrich_row_with_big_unit(r, current_period) for r in base_report["level1_lines"]]
        level2_rows = [_enrich_row_with_big_unit(r, current_period) for r in base_report["level2_lines"]]
        level1_total_cost = base_report["level1_total_cost"]
        level2_total_cost = base_report["level2_total_cost"]
        product_total_cost = base_report["product_total_cost"]

    context = {"periods": periods, "products": products, "current_period": current_period, "selected_product": selected_product,
               "qty": qty, "level1_rows": level1_rows, "level2_rows": level2_rows,
               "level1_total_cost": level1_total_cost, "level2_total_cost": level2_total_cost, "product_total_cost": product_total_cost}
    return render(request, "reports/product_cost_with_big_units.html", context)


# ✅ PDF (Playwright) — big units منتج واحد
def product_cost_with_big_units_pdf(request):
    period_id = request.GET.get("period")
    product_id = request.GET.get("product")
    qty_param = request.GET.get("qty") or "1"

    if not (period_id and product_id):
        return HttpResponse("يجب اختيار الفترة والمنتج أولاً", status=400)

    period = Period.objects.filter(id=period_id).first()
    product = Product.objects.filter(id=product_id).first()
    if not (period and product):
        return HttpResponse("فترة أو منتج غير صحيح", status=404)

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    base_report = build_product_cost_report(product, period, qty)
    level1_rows = [_enrich_row_with_big_unit(r, period) for r in base_report["level1_lines"]]
    level2_rows = [_enrich_row_with_big_unit(r, period) for r in base_report["level2_lines"]]

    report = {
        "product": product,
        "qty": qty,
        "level1_rows": level1_rows,
        "level2_rows": level2_rows,
        "level1_total_cost": base_report["level1_total_cost"],
        "level2_total_cost": base_report["level2_total_cost"],
        "product_total_cost": base_report["product_total_cost"],
    }

    filename = f"product_big_units_cost_{product.code}.pdf"

    return html_to_pdf_playwright(
        request=request,
        template_name="reports/product_cost_with_big_units_pdf.html",
        context={"current_period": period, "reports": [report], "title": "تقرير تكلفة المنتج (وحدات الشراء الكبيرة)"},
        filename=filename,
    )


# ✅ PDF (Playwright) — big units كل المنتجات
def product_cost_with_big_units_all_pdf(request):
    period_id = request.GET.get("period")
    qty_param = request.GET.get("qty") or "1"

    if not period_id:
        return HttpResponse("يجب اختيار الفترة أولاً", status=400)

    period = Period.objects.filter(id=period_id).first()
    if not period:
        return HttpResponse("فترة غير صحيحة", status=404)

    try:
        qty = Decimal(str(qty_param))
        if qty <= 0:
            qty = Decimal("1")
    except Exception:
        qty = Decimal("1")

    reports = []
    products = Product.objects.filter(is_sellable=True).order_by("name")
    for product in products:
        base_report = build_product_cost_report(product, period, qty)
        level1_rows = [_enrich_row_with_big_unit(r, period) for r in base_report["level1_lines"]]
        level2_rows = [_enrich_row_with_big_unit(r, period) for r in base_report["level2_lines"]]
        reports.append({
            "product": product,
            "qty": qty,
            "level1_rows": level1_rows,
            "level2_rows": level2_rows,
            "level1_total_cost": base_report["level1_total_cost"],
            "level2_total_cost": base_report["level2_total_cost"],
            "product_total_cost": base_report["product_total_cost"],
        })

    filename = f"products_big_units_cost_{period.id}.pdf"

    return html_to_pdf_playwright(
        request=request,
        template_name="reports/product_cost_with_big_units_pdf.html",
        context={"current_period": period, "reports": reports, "title": "تقرير تكلفة المنتجات (وحدات الشراء الكبيرة)"},
        filename=filename,
    )


# ─────────────────────────────
# Income Statement
# ─────────────────────────────
def income_statement(request):
    period_id = request.GET.get("period")
    periods = Period.objects.all().order_by("start_date")
    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    revenue = Decimal("0")
    if current_period:
        revenue = (
            SalesSummaryLine.objects
            .filter(summary__period=current_period)
            .aggregate(t=Sum("line_total"))["t"] or Decimal("0")
        )

    cogs = Decimal("0")
    if current_period:
        cogs = (
            SalesConsumption.objects
            .filter(summary__period=current_period)
            .aggregate(t=Sum("total_cost"))["t"] or Decimal("0")
        )

    gross_profit = revenue - cogs

    op = sa = ad = Decimal("0")
    if current_period:
        base = ExpenseLine.objects.filter(batch__period=current_period).select_related("item__category")
        op = base.filter(item__category__nature="OP").aggregate(t=Sum("amount"))["t"] or Decimal("0")
        sa = base.filter(item__category__nature="SA").aggregate(t=Sum("amount"))["t"] or Decimal("0")
        ad = base.filter(item__category__nature="AD").aggregate(t=Sum("amount"))["t"] or Decimal("0")

    total_expenses = op + sa + ad
    net_profit = gross_profit - total_expenses

    context = {
        "periods": periods,
        "current_period": current_period,
        "revenue": money(revenue),
        "cogs": money(cogs),
        "gross_profit": money(gross_profit),
        "op": money(op),
        "sa": money(sa),
        "ad": money(ad),
        "total_expenses": money(total_expenses),
        "net_profit": money(net_profit),
        "title": "قائمة الدخل",
    }
    return render(request, "reports/income_statement.html", context)


def income_statement_drilldown(request):
    period_id = request.GET.get("period")
    periods = Period.objects.all().order_by("start_date")
    current_period = Period.objects.filter(id=period_id).first() if period_id else get_default_period()

    D0 = Decimal("0")

    revenue = cogs = gross_profit = D0
    op = sa = ad = total_expenses = net_profit = D0

    cogs_rows = []
    op_rows = []
    sa_rows = []
    ad_rows = []

    if current_period:
        summaries = SalesSummary.objects.filter(period=current_period)
        revenue = sum((s.total_amount() for s in summaries), D0)

        cogs = (
            SalesConsumption.objects
            .filter(summary__period=current_period)
            .aggregate(t=Sum("total_cost"))["t"] or D0
        )

        gross_profit = revenue - cogs

        cogs_rows = list(
            SalesConsumption.objects
            .filter(summary__period=current_period, raw_material__isnull=False)
            .values(
                "raw_material__sku",
                "raw_material__name",
                "raw_material__ingredient_unit__name",
            )
            .annotate(
                qty_used=Coalesce(Sum("quantity_consumed"), D0),
                qty_sold=Coalesce(Sum("quantity_sold"), D0),
                total=Coalesce(Sum("total_cost"), D0),
            )
            .order_by("-total")
        )

        for r in cogs_rows:
            qty_used = r["qty_used"] or D0
            qty_sold = r["qty_sold"] or D0
            total = r["total"] or D0
            r["unit_cost_ingredient"] = (total / qty_used) if qty_used > 0 else D0
            r["unit_cost_per_sold_unit"] = (total / qty_sold) if qty_sold > 0 else D0

        batch = ExpenseBatch.objects.filter(period=current_period).first()
        if batch:
            base = ExpenseLine.objects.filter(batch=batch).select_related("item__category")

            def _rows(nature_code):
                return list(
                    base.filter(item__category__nature=nature_code)
                    .values("item__code", "item__name")
                    .annotate(total=Sum("amount"))
                    .order_by("-total")
                )

            op_rows = _rows("OP")
            sa_rows = _rows("SA")
            ad_rows = _rows("AD")

            op = sum((r["total"] or D0 for r in op_rows), D0)
            sa = sum((r["total"] or D0 for r in sa_rows), D0)
            ad = sum((r["total"] or D0 for r in ad_rows), D0)

        total_expenses = op + sa + ad
        net_profit = gross_profit - total_expenses

    context = {
        "title": "قائمة الدخل التفصيلية",
        "periods": periods,
        "current_period": current_period,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "op": op,
        "sa": sa,
        "ad": ad,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "cogs_rows": cogs_rows,
        "op_rows": op_rows,
        "sa_rows": sa_rows,
        "ad_rows": ad_rows,
    }
    return render(request, "reports/income_statement_drilldown.html", context)


###########################################################################################################################################################

from django.shortcuts import render
from django.utils.timezone import now

from expenses.models import Period
from .services.breakeven_engine import calc_breakeven


def breakeven_dashboard(request):
    # نفس فكرة income_statement: قائمة فترات + فترة حالية
    periods = Period.objects.all().order_by("-start_date")  # Period عندك فيه start_date/end_date :contentReference[oaicite:2]{index=2}

    period_id = request.GET.get("period")
    current_period = None

    if period_id:
        current_period = Period.objects.filter(id=period_id).first()

    # افتراضي: أحدث فترة
    if current_period is None:
        current_period = periods.first()

    # لو ما عندك ولا فترة
    if current_period is None:
        # رجّع صفحة بدون بيانات بدل الخطأ
        return render(request, "reports/breakeven_dashboard.html", {
            "title": "⚖️ تقرير نقطة التعادل والربحية",
            "periods": [],
            "current_period": None,
            "allocate": request.GET.get("allocate", "sales"),
            "r": None,
        })

    allocate = request.GET.get("allocate", "sales")  # sales|qty|cogs|cm

    # التاريخ يأتي من Period مباشرة
    date_from = current_period.start_date
    date_to = current_period.end_date

    result = calc_breakeven(
        date_from=date_from,
        date_to=date_to,
        allocate_fixed_method=allocate,
        include_per_sku=True,
    )

    totals = {
        "sales": sum((row["sales"] for row in result.per_sku), Decimal("0")),
        "consumption_cost": sum((row["consumption_cost"] for row in result.per_sku), Decimal("0")),
        "contribution_margin": sum((row["contribution_margin"] for row in result.per_sku), Decimal("0")),
        "fixed_allocated": sum((row["fixed_allocated"] for row in result.per_sku), Decimal("0")),
        "profit": sum((row["profit"] for row in result.per_sku), Decimal("0")),
    }

    return render(request, "reports/breakeven_dashboard.html", {
        "title": "⚖️ تقرير نقطة التعادل والربحية",
        "periods": periods,
        "current_period": current_period,
        "allocate": allocate,
        "r": result,
        "totals": totals,

        # اختياري
        "variable_rows": result.variable_expense_rows,
        "fixed_rows": result.fixed_expense_rows,
    })




########################################################################################################################
from django.shortcuts import render
from django.db.models import Exists, OuterRef
from expenses.models import Period
from sales.models import SalesSummary
from .services.breakeven_simulator_engine_v2 import calc_breakeven_simulator_by_period


def breakeven_simulator(request):
    allocate = request.GET.get("allocate", "sales")
    period_id = request.GET.get("period")

    # كل الفترات
    periods = Period.objects.all().order_by("-start_date")

    # ✅ حدد period
    current_period = None
    if period_id:
        current_period = Period.objects.filter(id=period_id).first()
    else:
        # ✅ اختر أول فترة لها SalesSummary (وبالتالي لها خطوط)
        periods_with_sales = periods.annotate(
            has_sales=Exists(
                SalesSummaryLine.objects.filter(summary__period=OuterRef("pk"))
            )
        ).filter(has_sales=True)
        current_period = periods_with_sales.first() or periods.first()

    # ✅ r نحسبه حتى لو مبيعات = 0 (عشان الهيدر يظهر دائمًا)
    r = None
    if current_period:
        r = calc_breakeven_simulator_by_period(
            period=current_period,
            allocate_fixed_method=allocate,
            include_per_sku=True,
        )

    return render(request, "reports/breakeven_simulator.html", {
        "title": "🧮 محاكي نقطة التعادل (تفاعلي)",
        "periods": periods,
        "current_period": current_period,
        "r": r,
        "allocate": allocate,
    })
