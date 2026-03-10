# hr/forms.py
from django import forms
from .models import Department

class PayrollAdjustmentHeaderForm(forms.Form):
    department = forms.ModelChoiceField(queryset=Department.objects.all(), label="الإدارة")
    year = forms.ChoiceField(choices=[(y, y) for y in range(2022, 2031)], label="السنة")
    month = forms.ChoiceField(choices=[(m, m) for m in range(1, 13)], label="الشهر")


# hr/admin.py
from django import forms
from django.forms.models import BaseInlineFormSet
from .models import Employee

class PayrollAdjustmentInlineFormSet(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # إذا تم تمرير الإدارة والشهر من `admin`
        initial_department = self.queryset.first().employee.department if self.queryset.exists() else None
        initial_month = self.queryset.first().payroll_month if self.queryset.exists() else None

        # إذا لم يكن هناك أي تعديل، أنشئ الأسطر من الموظفين
        if not self.queryset.exists() and initial_department and initial_month:
            employees = Employee.objects.filter(department=initial_department, is_active=True)
            self.initial = [
                {'employee': emp, 'payroll_month': initial_month}
                for emp in employees
            ]

from django import forms
from .models import LeaveRequest, Employee

class LeaveRequestForm(forms.ModelForm):
    available_balance = forms.CharField(label="رصيد الإجازات المتاحة", required=False, disabled=True)

    class Meta:
        model = LeaveRequest
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'available_balance']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['available_balance'].initial = self.instance.employee.remaining_leave_days(exclude_request=self.instance)
        elif 'employee' in self.data:
            try:
                employee = Employee.objects.get(pk=self.data.get('employee'))
                self.fields['available_balance'].initial = employee.remaining_leave_days()
            except Employee.DoesNotExist:
                pass
