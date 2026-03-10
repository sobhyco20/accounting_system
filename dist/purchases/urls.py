from django.urls import path
from . import views
from .views import supplier_ledger_report
from .views import purchases_by_supplier_product,purchase_return_invoice_pdf_view,purchase_invoice_pdf_view


app_name = "purchases"

urlpatterns = [
    
    
    path('reports/', views.purchase_reports, name='reports_home'),
    path('ajax/load-supplier-invoices/', views.load_supplier_invoices, name='load_supplier_invoices'),

path('reports/purchase-report/', views.purchase_report, name='purchase_report'),

    # تقرير المشتريات حسب المورد فقط (مع رسم بياني)
    path('reports/purchases-by-supplier/', views.purchases_by_supplier_report, name='purchases_by_supplier_report'),

    # تقرير المشتريات حسب المورد والصنف
    path('reports/purchases-by-supplier-product/', views.purchases_by_supplier_product, name='purchases_by_supplier_product'),

    # كشف حساب مورد (يشمل الرصيد، الفواتير، المردودات، السداد)
    path('reports/supplier-ledger/', views.supplier_ledger_report, name='supplier_ledger_report'),
    path('purchase-return/<int:pk>/pdf/', purchase_return_invoice_pdf_view, name='purchase_return_invoice_pdf'),
    path('purchase-invoice/<int:invoice_id>/pdf/', purchase_invoice_pdf_view, name='purchase_invoice_pdf'),
]






