from django.urls import path
from .views import main_dashboard

urlpatterns = [
    path('', main_dashboard, name='main_dashboard'),
]
