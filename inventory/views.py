from django.shortcuts import render
from django.http import HttpResponse
from django.db.models import Sum, Q
from inventory.models import  Warehouse, Product
import pandas as pd
from inventory.models import StockTransactionItem
from django.db.models import Sum, F


from django.shortcuts import render
from .models import Warehouse, Product, StockTransactionItem
from django.db.models import Sum
from decimal import Decimal

def stock_movement_report(request):
    warehouses = Warehouse.objects.all()
    products = Product.objects.all()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    warehouse_id = request.GET.get('warehouse')
    product_id = request.GET.get('product')
    transaction_type = request.GET.get('transaction_type')

    # تصفية حركات الأصناف
    transactions = StockTransactionItem.objects.select_related('transaction', 'product', 'transaction__warehouse').all()

    if date_from:
        transactions = transactions.filter(transaction__date__gte=date_from)
    if date_to:
        transactions = transactions.filter(transaction__date__lte=date_to)
    if warehouse_id:
        transactions = transactions.filter(transaction__warehouse_id=warehouse_id)
    if product_id:
        transactions = transactions.filter(product_id=product_id)
    if transaction_type:
        transactions = transactions.filter(transaction__transaction_type=transaction_type)
    
    transactions = transactions.order_by('transaction__date')

    # إجماليات
    total_quantity = transactions.aggregate(qty=Sum('quantity'))['qty'] or 0
    total_cost = sum(t.quantity * t.cost for t in transactions)

    # إضافة إجمالي كل حركة لاستخدامه في القالب
    for t in transactions:
        t.total = t.quantity * t.cost

    context = {
        'transactions': transactions,
        'warehouses': warehouses,
        'products': products,
        'total_quantity': total_quantity,
        'total_cost': total_cost,
    }
    return render(request, 'inventory/reports/stock_movement.html', context)


#################################################################################################


#################################################################################################################################
from inventory.models import StockTransactionItem
from django.http import JsonResponse

def get_product_unit_cost(request, product_id):
    items = StockTransactionItem.objects.filter(
        product_id=product_id,
        transaction__transaction_type='in'  # تأكد من أنه مطابق لقيمة القاعدة
    )

    total_cost = 0
    total_qty = 0

    for item in items:
        cost = item.cost or 0  # استبدال None بـ 0
        qty = item.quantity or 0

        total_cost += cost * qty
        total_qty += qty

    average_cost = (total_cost / total_qty) if total_qty > 0 else 0

    return JsonResponse({'average_cost': round(average_cost, 2)})



# inventory/views.py

from django.shortcuts import render

def reports_home(request):
    return render(request, 'inventory/reports/reports_home.html')


from django.db.models import Sum, Q, F
import pandas as pd
from django.http import HttpResponse
from django.shortcuts import render
from decimal import Decimal
from .models import StockTransactionItem, Warehouse, Product, OpeningStockItem


def product_balances_report(request):
    warehouse_id = request.GET.get('warehouse')
    export = request.GET.get('export')

    transactions = StockTransactionItem.objects.select_related('transaction', 'product')
    if warehouse_id:
        transactions = transactions.filter(transaction__warehouse_id=warehouse_id)

    balances = (
        transactions.values('product_id', 'product__name')
        .annotate(
            total_in=Sum('quantity', filter=Q(transaction__transaction_type='in')),
            total_out=Sum('quantity', filter=Q(transaction__transaction_type='out')),
        )
    )

    results = []
    for b in balances:
        product_id = b['product_id']
        product_name = b['product__name']

        opening_items = OpeningStockItem.objects.filter(product_id=product_id)
        if warehouse_id:
            opening_items = opening_items.filter(balance__warehouse_id=warehouse_id)

        opening_qty = opening_items.aggregate(total=Sum('quantity'))['total'] or 0
        opening_cost_total = opening_items.aggregate(
            cost_total=Sum(F('quantity') * F('unit_cost'))
        )['cost_total'] or 0

        total_in = b['total_in'] or 0
        total_out = b['total_out'] or 0
        current_balance = opening_qty + total_in - total_out

        movement_cost_total = transactions.filter(
            product_id=product_id, transaction__transaction_type='in'
        ).aggregate(
            total=Sum(F('quantity') * F('cost'))
        )['total'] or 0

        total_cost = Decimal(opening_cost_total) + Decimal(movement_cost_total)
        total_qty = Decimal(opening_qty) + Decimal(total_in)
        avg_cost = (total_cost / total_qty) if total_qty > 0 else Decimal('0')
        total_value = Decimal(current_balance) * avg_cost

        results.append({
            'product_name': product_name,
            'opening_qty': opening_qty,
            'total_in': total_in,
            'total_out': total_out,
            'balance': current_balance,
            'avg_cost': round(avg_cost, 2),
            'total_value': round(total_value, 2),
        })

    if export:
        df = pd.DataFrame(results)
        df = df.rename(columns={
            'product_name': 'اسم الصنف',
            'opening_qty': 'رصيد أول المدة',
            'total_in': 'إجمالي الإدخال',
            'total_out': 'إجمالي الإخراج',
            'balance': 'الرصيد الحالي',
            'avg_cost': 'متوسط التكلفة',
            'total_value': 'إجمالي القيمة',
        })
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=product_balances.xlsx'
        df.to_excel(response, index=False)
        return response

    warehouses = Warehouse.objects.all()
    context = {
        'results': results,
        'warehouses': warehouses,
        'request': request,
    }
    return render(request, 'inventory/reports/product_balances.html', context)





from django.shortcuts import render
from inventory.models import StockTransactionItem, Product, Warehouse
from django.db.models import Sum, F, FloatField
from django.http import HttpResponse
import csv

def stock_movement_report(request):
    transactions = StockTransactionItem.objects.select_related(
        'transaction', 'product', 'transaction__warehouse'
    )

    # --- فلترة حسب الطلب ---
    product_id = request.GET.get('product')
    warehouse_id = request.GET.get('warehouse')
    transaction_type = request.GET.get('transaction_type')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    if product_id:
        transactions = transactions.filter(product_id=product_id)

    if warehouse_id:
        transactions = transactions.filter(transaction__warehouse_id=warehouse_id)

    if transaction_type:
        transactions = transactions.filter(transaction__transaction_type=transaction_type)

    if date_from:
        transactions = transactions.filter(transaction__date__gte=date_from)

    if date_to:
        transactions = transactions.filter(transaction__date__lte=date_to)

    # --- الحسابات ---
    transactions = transactions.annotate(total=F('quantity') * F('cost'))

    total_quantity = transactions.aggregate(qty=Sum('quantity'))['qty'] or 0
    total_cost = transactions.aggregate(total=Sum(F('quantity') * F('cost'), output_field=FloatField()))['total'] or 0

    # --- التصدير إلى Excel (CSV) ---
    if request.GET.get('export') == '1':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="stock_movement.csv"'
        writer = csv.writer(response)
        writer.writerow(['التاريخ', 'الصنف', 'نوع الحركة', 'المستودع', 'الكمية', 'التكلفة', 'الإجمالي'])

        for t in transactions:
            writer.writerow([
                t.transaction.date,
                t.product.name,
                t.transaction.get_transaction_type_display(),
                t.transaction.warehouse.name,
                f"{t.quantity:.2f}",
                f"{t.cost:.2f}",
                f"{t.quantity * t.cost:.2f}"
            ])
        return response

    # --- تمرير البيانات للقالب ---
    context = {
        'transactions': transactions,
        'products': Product.objects.all(),
        'warehouses': Warehouse.objects.all(),
        'total_quantity': total_quantity,
        'total_cost': total_cost,
    }

    return render(request, 'inventory/reports/stock_movement_report.html', context)


from django import forms
from datetime import date


class ProfitFilterForm(forms.Form):
    start_date = forms.DateField(
        label="من تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date(2025, 1, 1)
    )
    end_date = forms.DateField(
        label="إلى تاريخ",
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=date(2025, 12, 31)
    )

#############################################################################################################################


from django.shortcuts import render
from django import forms
from datetime import date
from django.db.models import Sum, F
from inventory.models import Product, StockTransactionItem
from sales.models import SalesInvoiceItem, SalesReturnItem, SalesRepresentative

def product_profit_report(request):
    class ProfitFilterForm(forms.Form):
        date_from = forms.DateField(label="من تاريخ", widget=forms.DateInput(attrs={"type": "date"}), initial=date(2025, 1, 1))
        date_to = forms.DateField(label="إلى تاريخ", widget=forms.DateInput(attrs={"type": "date"}), initial=date(2025, 12, 31))
        product = forms.ModelChoiceField(queryset=Product.objects.all(), required=False, label="الصنف")
        rep = forms.ModelChoiceField(queryset=SalesRepresentative.objects.all(), required=False, label="المندوب")

    form = ProfitFilterForm(request.GET or None)
    results = []

    total_sales_qty = total_return_qty = total_net_qty = 0
    total_sales = total_returns = total_net_sales = 0
    total_cost = total_profit = 0

    if form.is_valid():
        date_from = form.cleaned_data["date_from"]
        date_to = form.cleaned_data["date_to"]
        product_filter = form.cleaned_data["product"]
        rep = form.cleaned_data["rep"]

        products = Product.objects.all()
        if product_filter:
            products = products.filter(id=product_filter.id)

        for product in products:
            # ✅ المبيعات (سعر بدون ضريبة)
            sales_qs = SalesInvoiceItem.objects.filter(
                invoice__date__range=(date_from, date_to),
                product=product
            )
            if rep:
                sales_qs = sales_qs.filter(invoice__sales_rep=rep)

            sales_qty = sales_qs.aggregate(qty=Sum("quantity"))["qty"] or 0
            sales_total = sales_qs.aggregate(total=Sum("total_before_tax"))["total"] or 0

            # ✅ مردودات المبيعات (سعر بدون ضريبة)
            return_qs = SalesReturnItem.objects.filter(
                sales_return__date__range=(date_from, date_to),
                product=product
            )
            if rep:
                return_qs = return_qs.filter(sales_return__sales_rep=rep)

            return_qty = return_qs.aggregate(qty=Sum("quantity"))["qty"] or 0
            return_total = return_qs.aggregate(total=Sum("total_before_tax"))["total"] or 0

            # ✅ الصافي
            net_qty = sales_qty - return_qty
            net_sales = sales_total - return_total

            # ✅ التكلفة (من فواتير المشتريات فقط)
            cost_items = StockTransactionItem.objects.filter(
                transaction__transaction_type='in',
                transaction__purchase_invoice__isnull=False,
                transaction__date__range=(date_from, date_to),
                product=product
            )

            total_cost_value = cost_items.aggregate(total=Sum('total_cost'))['total'] or 0
            total_cost_qty = cost_items.aggregate(total=Sum('quantity'))['total'] or 0
            average_cost = (total_cost_value / total_cost_qty) if total_cost_qty else 0

            # ✅ متوسط سعر البيع (بدون ضريبة)
            average_price = (net_sales / net_qty) if net_qty else 0

            # ✅ فرق السعر
            price_diff = average_price - average_cost

            # ✅ مجمل الربح
            profit = price_diff * net_qty

            # ✅ الهامش
            margin = (profit / net_sales * 100) if net_sales else 0

            # ✅ التجميع
            total_sales_qty += sales_qty
            total_return_qty += return_qty
            total_net_qty += net_qty
            total_sales += sales_total
            total_returns += return_total
            total_net_sales += net_sales
            total_cost += average_cost * net_qty
            total_profit += profit

            results.append({
                "product": product,
                "rep": rep.name if rep else "الكل",
                "sales_qty": sales_qty,
                "return_qty": return_qty,
                "net_qty": net_qty,
                "sales_total": sales_total,
                "return_total": return_total,
                "net_sales": net_sales,
                "average_price": average_price,
                "average_cost": average_cost,
                "price_diff": price_diff,
                "profit": profit,
                "margin": margin,
            })

    return render(request, "inventory/reports/product_profit_report.html", {
        "form": form,
        "results": results,
        "products": Product.objects.all(),
        "reps": SalesRepresentative.objects.all(),
        "total_sales_qty": total_sales_qty,
        "total_return_qty": total_return_qty,
        "total_net_qty": total_net_qty,
        "total_sales": total_sales,
        "total_returns": total_returns,
        "total_net_sales": total_net_sales,
        "total_cost": total_cost,
        "total_profit": total_profit,
    })
