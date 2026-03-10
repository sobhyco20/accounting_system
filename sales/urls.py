from django.urls import path
from django.shortcuts import redirect
from . import views

from .views import (
    sales_by_customer_report_view,
    customer_ledger_report_view,
    sales_by_product_and_customer_report_view,
    aging_report, invoice_pdf_view, sales_return_invoice_pdf_view,
    rep_sales_purchases_report,
    commission_report_view
)

app_name = 'sales'

urlpatterns = [
    # ✅ Redirect للمسار الجديد داخل portal
    path('invoices/', lambda request: redirect('/app/sales/invoices/'), name='invoice_list'),

    # ❌ لا تتركه لأنه نفس المسار (سيصير تعارض)
    # path('invoices/', views.sales_invoice_list, name='invoice_list'),

    path('invoices/<int:pk>/', views.sales_invoice_detail, name='invoice_detail'),

    path('returns/', views.sales_return_list, name='return_list'),
    path('customers/', views.customer_list, name='customer_list'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('reports/', views.reports_home, name='reports_home'),

    path('reports/sales-by-customer/', sales_by_customer_report_view, name='sales_by_customer_report'),
    path('reports/customer-ledger-view/', customer_ledger_report_view, name='customer_ledger_report'),
    path('reports/sales-by-product-and-customer/', sales_by_product_and_customer_report_view, name='sales_by_product_and_customer_report'),
    path('reports/aging/', aging_report, name='aging_report'),
    path('sales-report/', views.sales_report, name='sales_report'),
    path('invoice/<int:invoice_id>/pdf/', invoice_pdf_view, name='invoice_pdf'),
    path('sales-return/<int:pk>/pdf/', sales_return_invoice_pdf_view, name='sales_return_invoice_pdf'),
    path('rep-sales-purchases/', rep_sales_purchases_report, name='rep_sales_purchases_report'),
    path("reports/commission/", commission_report_view, name="commission_report"),
]