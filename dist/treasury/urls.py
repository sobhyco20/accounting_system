from django.urls import path
from . import views

app_name = 'treasury'

urlpatterns = [
    path('reports/', views.reports_home, name='reports_home'),
    path('reports/treasury-movement-report/', views.treasury_movement_report, name='treasury_movement_report'),
]
