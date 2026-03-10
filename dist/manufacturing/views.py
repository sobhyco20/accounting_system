from django.shortcuts import render

def manufacturing_reports(request):
    return render(request, 'manufacturing/reports/dashboard.html')


# manufacturing/views.py
from django.shortcuts import render

def manufacturing_reports(request):
    return render(request, 'manufacturing/reports/dashboard.html')


# في views.py
from django.http import JsonResponse
from inventory.models import StockTransactionItem

def get_latest_unit_cost(request):
    product_id = request.GET.get("product_id")
    latest_cost_item = (
        StockTransactionItem.objects
        .filter(
            product_id=product_id,
            transaction__transaction_type='in',
            cost__isnull=False,
            cost__gt=0
        )
        .order_by('-transaction__date')
        .first()
    )

    unit_cost = latest_cost_item.cost if latest_cost_item else 0
    return JsonResponse({'unit_cost': float(unit_cost)})

################################################################################################################

# manufacturing/views.py
# views.py
# views.py

from django.http import JsonResponse
from .models import Product

def get_bom_components(request):
    product_id = request.GET.get('product_id')
    quantity = float(request.GET.get('quantity', 1))

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'المنتج غير موجود'})

    try:
        bom = product.bomtemplate  # تأكد من العلاقة
    except:
        return JsonResponse({'success': False, 'message': 'لا يوجد قالب مكونات مرتبط'})

    components = []
    for item in bom.items.all():
        q = item.quantity * quantity
        unit_cost = item.unit_cost
        components.append({
            'component_name': item.component.name,
            'quantity': q,
            'unit_cost': unit_cost,
            'total': round(q * unit_cost, 2),
        })

    expenses = []
    for exp in bom.expenses.all():
        expenses.append({
            'name': exp.name,
            'amount': exp.amount,
        })

    return JsonResponse({'success': True, 'components': components, 'expenses': expenses})
#################################################################################################################################################
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from decimal import Decimal
from .models import (
    ProductionOrder, Product, ProductBOMItem, ProductBOMExpense,
    ProductionOrderComponent, ProductionOrderExpense
)

def update_bom(request, product_id, quantity):
    try:
        product = get_object_or_404(Product, pk=product_id)
        bom_items = ProductBOMItem.objects.filter(product=product)
        bom_expenses = ProductBOMExpense.objects.filter(product=product)

        last_order = ProductionOrder.objects.filter(product=product).last()
        if last_order:
            # حذف المكونات والمصروفات القديمة
            last_order.components.all().delete()
            last_order.expenses.all().delete()

            # إضافة المكونات الجديدة
            for item in bom_items:
                ProductionOrderComponent.objects.create(
                    order=last_order,
                    product=item.component,
                    quantity=item.quantity * Decimal(quantity),
                    unit_cost=item.component_cost or 0
                )

            # إضافة المصروفات الجديدة
            for expense in bom_expenses:
                ProductionOrderExpense.objects.create(
                    order=last_order,
                    name=expense.name,
                    cost=expense.cost
                )

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
    

##############################################################################################################
# views.py في manufacturing

from django.shortcuts import render
from .models import ProductionOrder, ProductionOrderComponent, ProductionOrderExpense

def reports_home(request):
    return render(request, 'manufacturing/reports/reports_home.html')

from django.utils.dateparse import parse_date
from django.utils import timezone
from .models import ProductionOrder

def production_orders_report(request):
    from_date = request.GET.get('from_date', '2026-01-01')
    to_date = request.GET.get('to_date', '2026-12-31')

    from_date_parsed = parse_date(from_date)
    to_date_parsed = parse_date(to_date)

    orders = ProductionOrder.objects.select_related('product', 'finished_goods_warehouse') \
        .filter(date__range=(from_date_parsed, to_date_parsed))

    context = {
        'orders': orders,
        'from_date': from_date,
        'to_date': to_date,
    }

    return render(request, 'manufacturing/reports/production_orders.html', context)



from django.utils.dateparse import parse_date

def scrap_report(request):
    from_date = request.GET.get('from_date', '2026-01-01')
    to_date = request.GET.get('to_date', '2026-12-31')

    from_date_parsed = parse_date(from_date)
    to_date_parsed = parse_date(to_date)

    orders = ProductionOrder.objects.select_related('product', 'scrap_warehouse') \
        .filter(scrap_quantity__isnull=False, date__range=(from_date_parsed, to_date_parsed))

    return render(request, 'manufacturing/reports/scrap.html', {'orders': orders})


def estimated_costs_report(request):
    orders = ProductionOrder.objects.all()
    return render(request, 'manufacturing/reports/estimated_costs.html', {'orders': orders})
    
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def manufacturing_reports_view(request):
    return render(request, 'manufacturing/reports.html')


from django.utils.dateparse import parse_date

def raw_materials_report(request):
    from_date = request.GET.get('from_date', '2026-01-01')
    to_date = request.GET.get('to_date', '2026-12-31')

    from_date_parsed = parse_date(from_date)
    to_date_parsed = parse_date(to_date)

    components = ProductionOrderComponent.objects.select_related('order', 'product') \
        .filter(order__date__range=(from_date_parsed, to_date_parsed))

    return render(request, 'manufacturing/reports/raw_materials.html', {
        'components': components
    })


def finished_products_report(request):
    from django.utils.dateparse import parse_date

    from_date = request.GET.get('from_date', '2026-01-01')
    to_date = request.GET.get('to_date', '2026-12-31')

    from_date_parsed = parse_date(from_date)
    to_date_parsed = parse_date(to_date)

    orders = ProductionOrder.objects.select_related('product', 'finished_goods_warehouse') \
        .filter(date__range=(from_date_parsed, to_date_parsed))

    return render(request, 'manufacturing/reports/finished_products.html', {
        'orders': orders
    })

