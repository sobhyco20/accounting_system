from django.contrib import admin
from django.urls import path
from .views import payroll_adjustment_view
from . import views
from hr.views import get_leave_balance

from .views import (
    payroll_adjustment_view,
    leave_balance_report,
    employee_monthly_leave_detail,
    payroll_summary_report,
    hr_reports_home,
)


app_name = "hr"


urlpatterns = [
    path('admin/', admin.site.urls),
    path('payroll-adjustments/', payroll_adjustment_view, name='payroll_adjustments'),
    path('payroll/<int:pk>/generate-lines/', views.generate_payroll_lines, name='payroll_generate_lines'),
    path('ajax/get-leave-balance/', views.get_leave_balance, name='get_leave_balance'),
    path('admin/hr/get-leave-balance/', get_leave_balance, name='get_leave_balance'),
    path('reports/', hr_reports_home, name='hr_reports_home'),
    path("reports/leave-summary/", views.leave_balance_report, name="leave_summary_report"), 
    path("reports/employee-monthly/", views.employee_monthly_leave_detail, name="employee_monthly_report"),
    path("reports/department-summary/", views.payroll_summary_report, name="department_summary_report"),
    path("reports/employee-payroll-detail/", views.employee_monthly_payroll_detail, name="employee_payroll_detail_report"), 
    path('leave-allowance-summary/', views.leave_allowance_summary_report, name='leave_allowance_summary_report'),
    path("eos-reward-summary/", views.eos_reward_summary_report, name="eos_reward_summary_report"),

  


]
