
# hr/views.py
from django.shortcuts import render, redirect
from datetime import date
from .models import Employee, Department,PayrollAdjustmentLine,PayrollLine,LeaveRequest
from .forms import PayrollAdjustmentHeaderForm
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import PayrollBatch
from datetime import date, datetime
from decimal import Decimal


from hr.models import PayrollAdjustmentHeader, PayrollAdjustmentLine, Employee
from datetime import date

def payroll_adjustment_view(request):
    form = PayrollAdjustmentHeaderForm(request.POST or None)
    employees = []

    if request.method == 'POST' and form.is_valid():
        dept = form.cleaned_data['department']
        year = int(form.cleaned_data['year'])
        month = int(form.cleaned_data['month'])

        # احصل على رأس التعديل أو أنشئه
        header, created = PayrollAdjustmentHeader.objects.get_or_create(
            department=dept,
            year=year,
            month=month
        )

        employees = Employee.objects.filter(department=dept, is_active=True)

        if 'save' in request.POST:
            for emp in employees:
                absence_days = int(request.POST.get(f'absence_{emp.id}', 0))
                deduction_amount = float(request.POST.get(f'deduction_{emp.id}', 0))

                # أنشئ أو حدّث السطر
                PayrollAdjustmentLine.objects.update_or_create(
                    header=header,
                    employee=emp,
                    defaults={
                        'absence_days': absence_days,
                        'deduction_amount': deduction_amount,
                    }
                )
            return redirect(request.path + '?success=1')

    context = {
        'form': form,
        'employees': employees,
        'submitted': request.method == 'POST' and form.is_valid(),
    }
    return render(request, 'admin/hr/payrollbatch/payroll_adjustment_form.html', context)



def generate_payroll_lines(request, pk):
    payroll = PayrollBatch.objects.get(pk=pk)
    # قم بتنفيذ منطق التوليد بناءً على التعديلات
    payroll.generate_lines_from_adjustments()  # تأكد أن هذه الدالة موجودة
    messages.success(request, "تم توليد تفاصيل المسير من الخصومات.")
    return HttpResponseRedirect(reverse('admin:hr_payrollbatch_change', args=[pk]))


def post_accrual_view(self, request, pk):
    obj = self.get_object(request, pk)
    if obj:
        obj.post_accrual()
        self.message_user(request, "تم ترحيل قيد الاستحقاق بنجاح.")
    return redirect('admin:hr_payrollbatch_change', obj.pk)

def post_payment_view(self, request, pk):
    obj = self.get_object(request, pk)
    if obj:
        obj.post_payment()
        self.message_user(request, "تم ترحيل قيد الصرف بنجاح.")
    return redirect('admin:hr_payrollbatch_change', obj.pk)

from django.http import JsonResponse
from .models import Employee
from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def get_leave_balance(request):
    emp_id = request.GET.get('employee_id')
    try:
        emp = Employee.objects.get(id=emp_id)
        return JsonResponse({'balance': emp.available_leave_balance})
    except Employee.DoesNotExist:
        return JsonResponse({'balance': 0})


#____________________________________________________________________________________________




from django.shortcuts import render

def hr_reports_home(request):
    return render(request, 'hr/reports/reports_home.html')



def leave_balance_report(request):
    from datetime import datetime

    department_id = request.GET.get('department')
    employee_id = request.GET.get('employee')

    employees = Employee.objects.filter(is_active=True)
    if department_id:
        employees = employees.filter(department_id=department_id)
    if employee_id:
        employees = employees.filter(id=employee_id)

    data = []
    for emp in employees:
        data.append({
            'employee': emp,
            'employee_name': emp.full_name,
            'department': emp.department.name if emp.department else '',
            'accrued': emp.accrued_leave_days(),
            'used': emp.used_leave_days(),
            'remaining': emp.remaining_leave_days(),
        })

    context = {
        'data': data,
        'departments': Department.objects.all(),
        'employees': Employee.objects.filter(is_active=True),
        'selected_department': int(department_id) if department_id else None,
        'selected_employee': int(employee_id) if employee_id else None,
    }
    return render(request, 'hr/reports/leave_balance.html', context)


from datetime import datetime
from django.shortcuts import render
from .models import Employee, LeaveRequest, Department
from datetime import datetime
from django.shortcuts import render
from .models import Employee, LeaveRequest, Department

def employee_monthly_leave_detail(request):
    department_id = request.GET.get('department')
    employee_id = request.GET.get('employee')
    month = int(request.GET.get('month', datetime.today().month))
    year = int(request.GET.get('year', datetime.today().year))

    employees = Employee.objects.filter(is_active=True)
    if department_id:
        employees = employees.filter(department_id=department_id)

    leaves = LeaveRequest.objects.filter(
        start_date__year=year,
        start_date__month=month,
        employee__in=employees
    ).select_related('employee', 'employee__department', 'employee__division')

    if employee_id:
        leaves = leaves.filter(employee_id=employee_id)

    context = {
        'departments': Department.objects.all(),
        'employees': employees,
        'leaves': leaves,
        'selected_department': int(department_id) if department_id else None,
        'selected_employee': int(employee_id) if employee_id else None,
        'month': month,
        'year': year,
        'months': range(1, 13),
        'years': range(datetime.today().year - 5, datetime.today().year + 2),
    }
    return render(request, 'hr/reports/employee_leave_detail.html', context)


from datetime import datetime
from django.shortcuts import render
from hr.models import PayrollBatch, Department, Employee
from datetime import datetime
from django.shortcuts import render
from .models import Department, Employee, PayrollBatch

def payroll_summary_report(request):
    department_id = request.GET.get('department')
    employee_id = request.GET.get('employee')
    month_str = request.GET.get('month')
    year_str = request.GET.get('year')

    today = datetime.today()

    try:
        month = int(month_str)
        if not (1 <= month <= 12):
            raise ValueError()
    except (ValueError, TypeError):
        month = today.month

    try:
        year = int(year_str)
    except (ValueError, TypeError):
        year = today.year

    batch_qs = PayrollBatch.objects.filter(month=month, year=year)
    if department_id and department_id.isdigit():
        batch_qs = batch_qs.filter(department_id=int(department_id))

    batch = batch_qs.first()
    lines = batch.lines.all() if batch else []

    if employee_id and employee_id.isdigit():
        lines = lines.filter(employee_id=int(employee_id))

    context = {
        'batch': batch,
        'lines': lines,
        'departments': Department.objects.all(),
        'employees': Employee.objects.filter(is_active=True),
        'selected_department': int(department_id) if department_id and department_id.isdigit() else None,
        'selected_employee': int(employee_id) if employee_id and employee_id.isdigit() else None,
        'month': month,
        'year': year,
        'months': range(1, 13),
        'years': range(today.year - 5, today.year + 2),
    }
    return render(request, 'hr/reports/payroll_summary.html', context)



#-------------------------------------------------------------------------------------------------
from datetime import datetime
from django.shortcuts import render
from hr.models import PayrollBatch, Department, Employee, PayrollLine

def employee_monthly_payroll_detail(request):
    department_id = request.GET.get('department')
    employee_id = request.GET.get('employee')
    month = int(request.GET.get('month', datetime.today().month))
    year = int(request.GET.get('year', datetime.today().year))

    # جميع الإدارات والموظفين النشطين
    departments = Department.objects.all()
    employees = Employee.objects.filter(is_active=True)

    # تصفية الموظفين حسب الإدارة أو موظف محدد
    if department_id and department_id.isdigit():
        department_id = int(department_id)
        employees = employees.filter(department_id=department_id)
    else:
        department_id = None

    if employee_id and employee_id.isdigit():
        employee_id = int(employee_id)
        employees = employees.filter(id=employee_id)
    else:
        employee_id = None

    # محاولة جلب الباتش المناسب
    batch_qs = PayrollBatch.objects.filter(month=month, year=year)
    if department_id:
        batch_qs = batch_qs.filter(department_id=department_id)

    batch = batch_qs.first()
    lines = PayrollLine.objects.filter(batch=batch, employee__in=employees) if batch else []

    context = {
        'departments': departments,
        'employees': Employee.objects.filter(is_active=True),
        'lines': lines,
        'batch': batch,
        'selected_department': department_id,
        'selected_employee': employee_id,
        'month': month,
        'year': year,
        'months': range(1, 13),
        'years': range(datetime.today().year - 5, datetime.today().year + 2),
    }
    return render(request, 'hr/reports/payroll_detail.html', context)



#-----------------------------------------------------------------------------------------

from django.shortcuts import render
from django.utils.dateparse import parse_date
from hr.models import Department, Employee, LeaveAllowance
from datetime import datetime

def leave_allowance_summary_report(request):
    department_id = request.GET.get('department')
    to_date_str = request.GET.get('to_date')
    to_date = parse_date(to_date_str) if to_date_str else datetime.today().date()

    employees = Employee.objects.filter(is_active=True)
    if department_id:
        employees = employees.filter(department_id=department_id)

    data = []
    for emp in employees:
        allowances = LeaveAllowance.objects.filter(employee=emp, pay_date__lte=to_date)
        total_paid = sum(a.total_amount for a in allowances)
        accrued_days = emp.get_accrued_leave_days_until(to_date)
        daily_rate = emp.get_daily_leave_allowance_rate()
        total_entitled = Decimal(str(accrued_days)) * daily_rate
        remaining = total_entitled - total_paid

        data.append({
            'employee': emp,
            'department': emp.department.name if emp.department else '',
            'total_paid': total_paid,
            'total_entitled': total_entitled,
            'remaining': remaining,
        })

    context = {
        'departments': Department.objects.all(),
        'data': data,
        'selected_department': int(department_id) if department_id else None,
        'to_date': to_date,
    }
    return render(request, 'hr/reports/leave_allowance_summary.html', context)



#-------------------------------------------------------------------------------------
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta

def calculate_eos_reward(employee, to_date, policy):
    if not employee.hire_date or not policy:
        return Decimal("0.00")

    delta = relativedelta(to_date, employee.hire_date)
    years = delta.years
    months = delta.months
    days = delta.days

    total_years = years + (months / 12) + (days / 365.0)

    first_years = min(total_years, policy.first_years)
    remaining_years = max(total_years - first_years, 0)

    salary = employee.base_salary or Decimal("0.00")

    reward_days = (
        Decimal(first_years) * policy.reward_per_year_first +
        Decimal(remaining_years) * policy.reward_per_year_after
    )

    reward = (salary / Decimal("30.0")) * reward_days
    reward *= (policy.percentage or 100) / 100

    return round(reward, 2)


#--------------------------------------------------------------------------------------
from django.shortcuts import render
from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from hr.models import Employee, EndOfServicePolicy


def eos_reward_summary_report(request):
    department_id = request.GET.get("department")
    to_date_str = request.GET.get("to_date")
    to_date = date.today()
    if to_date_str:
        try:
            to_date = date.fromisoformat(to_date_str)
        except:
            pass

    employees = Employee.objects.filter(is_active=True)
    if department_id:
        employees = employees.filter(department_id=department_id)

    # 💡 السياسة الافتراضية = صرف كامل المستحقات
    default_policy = EndOfServicePolicy.objects.filter(name__icontains="صرف كامل المستحقات").first()

    data = []
    for emp in employees:
        if not emp.hire_date:
            continue

        delta = relativedelta(to_date, emp.hire_date)
        years = delta.years
        months = delta.months
        days = delta.days

        salary = emp.base_salary or Decimal("0.00")
        reward = Decimal("0.00")
        policy_name = "غير معرف"

        if default_policy:
            reward = calculate_eos_reward(emp, to_date, default_policy)
            policy_name = default_policy.name

        data.append({
            "employee_name": emp.full_name,
            "department": emp.department.name if emp.department else "",
            "hire_date": emp.hire_date,
            "years": years,
            "months": months,
            "days": days,
            "salary": salary,
            "reward": reward,
            "policy": policy_name,
        })

    context = {
        "data": data,
        "departments": Employee.objects.values_list("department__id", "department__name").distinct(),
        "selected_department": int(department_id) if department_id else None,
        "to_date": to_date,
    }

    return render(request, "hr/reports/eos_reward_summary.html", context)
