from django.urls import path
from . import views

urlpatterns = [
    path("", views.root_redirect, name="root"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("app/", views.app_home, name="app_home"),

    # SALES
    path("app/sales/invoices/", views.app_sales_invoice_list, name="app_sales_invoice_list"),
    path("app/sales/invoices/new/", views.app_sales_invoice_create, name="app_sales_invoice_create"),
    path("app/sales/invoices/<int:pk>/edit/", views.app_sales_invoice_edit, name="app_sales_invoice_edit"),

    # اختياري للعرض فقط
    path("app/sales/invoices/<int:pk>/", views.sales_invoice_detail, name="sales_invoice_detail"),


    path("app/sales/returns/", views.app_sales_return_list, name="app_sales_return_list"),
    path("app/sales/returns/new/", views.app_sales_return_create, name="app_sales_return_create"),
    path("app/sales/returns/<int:pk>/edit/", views.app_sales_return_edit, name="app_sales_return_edit"),

        # PURCHASES (Returns)
    path("app/purchases/returns/", views.app_purchase_return_list, name="app_purchase_return_list"),
    path("app/purchases/returns/new/", views.app_purchase_return_create, name="app_purchase_return_create"),
    path("app/purchases/returns/<int:pk>/edit/", views.app_purchase_return_edit, name="app_purchase_return_edit"),

    # PURCHASES
    path("app/purchases/invoices/", views.app_purchase_invoice_list, name="app_purchase_invoice_list"),
    path("app/purchases/invoices/new/", views.app_purchase_invoice_create, name="app_purchase_invoice_create"),
    path("app/purchases/invoices/<int:pk>/edit/", views.app_purchase_invoice_edit, name="app_purchase_invoice_edit"),


    path("app/sales/reports/", views.app_sales_reports, name="app_sales_reports"),
    path("app/purchases/reports/", views.app_purchase_reports, name="app_purchase_reports"),


    

    path("app/inventory/opening-balances/", views.app_opening_balance_list, name="app_opening_balance_list"),
    path("app/inventory/opening-balances/new/", views.app_opening_balance_create, name="app_opening_balance_create"),
    path("app/inventory/opening-balances/<int:pk>/edit/", views.app_opening_balance_edit, name="app_opening_balance_edit"),
    path("app/inventory/opening-balances/<int:pk>/post/", views.app_opening_balance_post, name="app_opening_balance_post"),
    path("app/inventory/opening-balances/<int:pk>/unpost/", views.app_opening_balance_unpost, name="app_opening_balance_unpost"),

    path("app/inventory/transactions/", views.app_stock_tx_list, name="app_stock_tx_list"),
    path("app/inventory/transactions/new/", views.app_stock_tx_create, name="app_stock_tx_create"),
    path("app/inventory/transactions/<int:pk>/edit/", views.app_stock_tx_edit, name="app_stock_tx_edit"),
    path("app/inventory/transactions/<int:pk>/post/", views.app_stock_tx_post, name="app_stock_tx_post"),
    path("app/inventory/transactions/<int:pk>/unpost/", views.app_stock_tx_unpost, name="app_stock_tx_unpost"),

    path("app/inventory/reports/", views.app_inventory_reports, name="app_inventory_reports"),
]