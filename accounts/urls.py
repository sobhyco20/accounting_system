# accounts/urls.py
from django.urls import path
from . import views
from .views import opening_balances_view,cash_flow_report_view, financial_statement_report_view


app_name = 'accounts'

urlpatterns = [



    
    path('reports/', views.accounts_reports_home, name='reports_home'),
    path('reports/ledger/', views.ledger_report, name='ledger_report'),
    path('reports/', views.accounts_reports_home, name='accounts_home'),
    path('reports/trial-balance/', views.trial_balance_view, name='trial_balance'),
    path('reports/opening-balances/', opening_balances_view, name='opening-balances'),
    path('income-statement/', views.income_statement_view, name='income_statement'),
    path('balance-sheet/', views.balance_sheet_view, name='balance_sheet'),
    path('reports/cash-flow/', cash_flow_report_view, name='cash_flow_report'),
    path("reports/statement-report/", financial_statement_report_view, name="financial_statement_report"),
    path('reports/vat-report/', views.vat_report_view, name='vat_report'),


]
