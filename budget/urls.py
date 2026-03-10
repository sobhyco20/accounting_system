# budget/urls.py
from django.urls import path
from . import views

app_name = 'budget'

urlpatterns = [
    path('<int:pk>/entries/', views.budget_entry_view, name='budget_entry'),
    path('reports/', views.budget_reports_home, name='reports_home'),
    path('reports/summary/', views.budget_summary_report, name='budget_summary_report'),
    path('reports/comparison/', views.budget_comparison_report, name='budget_comparison_report'),
    path('reports/by-account/', views.budget_by_account_report, name='budget_by_account_report'),
]
