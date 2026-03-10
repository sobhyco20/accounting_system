from django.urls import path
from . import views
from .views import get_bom_components
from manufacturing.views import update_bom

app_name = 'manufacturing'

urlpatterns = [
    path('reports/', views.manufacturing_reports, name='manufacturing_reports'),
    path('get-latest-unit-cost/', views.get_latest_unit_cost, name='get_latest_unit_cost'),
    path('get-bom-components/', get_bom_components, name='get_bom_components'),
    path('update_bom/<int:order_id>/<str:quantity>/', update_bom, name='update_bom'),

    path('reports/', views.reports_home, name='reports_home'),
    path('reports/production-orders/', views.production_orders_report, name='production_orders_report'),
    path('reports/raw-materials/', views.raw_materials_report, name='raw_materials_report'),
    path('reports/finished-products/', views.finished_products_report, name='finished_products_report'),
    path('reports/scrap/', views.scrap_report, name='scrap_report'),
    path('reports/estimated-costs/', views.estimated_costs_report, name='estimated_costs_report'),
    path('reports/', views.manufacturing_reports_view, name='reports'),
]







