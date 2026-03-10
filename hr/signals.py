# hr/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PayrollBatch, PayrollLine
from hr.models import Employee  # استيراد مباشر لتفادي import دائري

@receiver(post_save, sender=PayrollBatch)
def generate_payroll_lines(sender, instance, created, **kwargs):
    if created:
        employees = Employee.objects.filter(department=instance.department, is_active=True)
        for emp in employees:
            PayrollLine.objects.create(
                batch=instance,
                employee=emp,
                base_salary=emp.base_salary,
                housing_allowance=emp.housing_allowance,
                transport_allowance=emp.transport_allowance,
                other_allowances=emp.other_allowances,
                bonuses=emp.bonuses,
                deductions=emp.deductions,
            )
        instance.update_totals()
