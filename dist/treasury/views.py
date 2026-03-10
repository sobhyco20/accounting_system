from django.shortcuts import render
from django.db.models import Sum
from hr.models import Employee
from .models import TreasuryBox, TreasuryVoucher
from datetime import date

def treasury_movement_report(request):
    # التواريخ الافتراضية
    default_from_date = date(2025, 1, 1)
    default_to_date = date(2025, 12, 31)

    from_date = request.GET.get('from_date') or default_from_date
    to_date = request.GET.get('to_date') or default_to_date
    selected_box = request.GET.get('box')
    selected_employee = request.GET.get('employee')

    boxes = TreasuryBox.objects.all()
    employees = Employee.objects.all()

    data = {}

    for box in boxes:
        vouchers = TreasuryVoucher.objects.filter(box=box)

        # تحويل التواريخ إلى كائنات تاريخ فعلية إذا كانت نصوصًا
        if isinstance(from_date, str):
            from_date = date.fromisoformat(from_date)
        if isinstance(to_date, str):
            to_date = date.fromisoformat(to_date)

        vouchers = vouchers.filter(date__gte=from_date, date__lte=to_date)

        if selected_employee:
            vouchers = vouchers.filter(responsible_id=selected_employee)

        opening = box.opening_balance or 0
        receipt_total = vouchers.filter(voucher_type='receipt').aggregate(total=Sum('amount'))['total'] or 0
        payment_total = vouchers.filter(voucher_type='payment').aggregate(total=Sum('amount'))['total'] or 0
        balance = opening + receipt_total - payment_total

        voucher_list = vouchers.order_by('date')

        data[box] = {
            'opening': opening,
            'receipt': receipt_total,
            'payment': payment_total,
            'balance': balance,
            'vouchers': voucher_list,
        }

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'selected_box': int(selected_box) if selected_box else None,
        'selected_employee': int(selected_employee) if selected_employee else None,
        'boxes': boxes,
        'employees': employees,
        'data': data,
    }
    return render(request, 'treasury/reports/treasury_movement_report.html', context)


from django.shortcuts import render

def reports_home(request):
    return render(request, 'treasury/reports/reports_home.html')
