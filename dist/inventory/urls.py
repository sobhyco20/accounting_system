from django.urls import path
from .views import stock_movement_report
from .views import product_balances_report
from . import views
from .views import get_product_unit_cost


app_name = 'inventory' 


urlpatterns = [
    path('reports/product-balances/', product_balances_report, name='product_balances'),
    path('reports/stock-movement/', stock_movement_report, name='stock_movement'),
    path('api/product-cost/<int:product_id>/', get_product_unit_cost, name='get_product_unit_cost'),
    path('reports/', views.reports_home, name='reports_home'),
    path("reports/product-profit/", views.product_profit_report, name="product_profit_report"),

   



]

