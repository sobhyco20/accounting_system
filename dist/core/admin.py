from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.template.response import TemplateResponse

class CustomAdminSite(admin.AdminSite):
    site_header = "لوحة التحكم المحاسبية"
    site_title = "البرنامج المحاسبي"
    index_title = "الصفحة الرئيسية"

    def index(self, request, extra_context=None):
        if extra_context is None:
            extra_context = {}
        extra_context['custom_reports'] = [
            {
                'title': ' تقرير المبيعات والمردودات',
                'url': reverse('sales:sales_report')
            },
            {
                'title': '📆 تقرير أعمار الديون',
                'url': reverse('sales:aging_report')
            },
            {
                'title': '👥 تقرير بيانات العملاء',
                'url': reverse('sales:customer_list')
            },
        ]
        return TemplateResponse(request, "admin/custom_index.html", extra_context)

# استخدم الموقع الجديد
custom_admin_site = CustomAdminSite(name='custom_admin')


# core/admin.py
from django.contrib import admin
from .models import CompanyProfile

@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = ['name']
