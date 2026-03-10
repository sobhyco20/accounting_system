from django.contrib import admin
from django.urls import path
from django.urls import path, include
from core.admin import custom_admin_site
from .views import home_view
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('admin/', custom_admin_site.urls),
    path('inventory/', include('inventory.urls')),
    path('manufacturing/', include('manufacturing.urls')),
    path('sales/', include('sales.urls')),
    path('accounts/', include(('accounts.urls', 'accounts'), namespace='accounts')),
    path('purchases/', include('purchases.urls')),
    path('', include('dashboard.urls')),
    path('budget/', include('budget.urls')),
    path("hr/", include("hr.urls")),
    path('treasury/', include('treasury.urls')),

    

]


if settings.DEBUG:
    if hasattr(settings, 'STATICFILES_DIRS') and settings.STATICFILES_DIRS:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    else:
        urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)