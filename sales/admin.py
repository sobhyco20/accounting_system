from decimal import Decimal
from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.dateparse import parse_date
from django.db.models import Sum, F
from django.http import HttpResponse, HttpResponseRedirect
from datetime import datetime, timedelta
from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from .models import CustomerPayment
# استيراد الموديلات من نفس الموديول الخاص بالمبيعات فقط:
from .models import (
    CustomerGroup, Customer, SalesInvoice, SalesInvoiceItem,
    SalesReturn, SalesReturnItem, CustomerPayment,SalesRepresentative


)

from treasury.models import TreasuryBox, BankAccount

# استيراد Product من inventory بشكل آمن (تتم في ملف inventory/admin.py فقط)
from inventory.models import Product

# استيراد الفورم الخاص بالأصناف في الفاتورة والمرتجع
from .forms import SalesInvoiceItemForm, SalesReturnItemForm
from .forms import CustomerPaymentForm
from django.templatetags.static import static

# --------------------------------------------------
# مجموعات العملاء والعملاء

@admin.register(CustomerGroup)
class CustomerGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'account']
    search_fields = ['name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'group', 'opening_debit', 'opening_credit', 'phone']
    readonly_fields = ['code']
    list_filter = ['group']
    search_fields = ['code', 'name', 'phone']
    autocomplete_fields = ['account', 'sales_account', 'vat_account']

    
    fieldsets = (
        ("بيانات العميل", {
            'fields': ('code', 'name','tax_number' ,'group', 'phone', 'email', 'address')
        }),
        ("الأرصدة الافتتاحية", {
            'fields': ('opening_debit', 'opening_credit')
        }),
        ("الحسابات المرتبطة", {
            'fields': (
                'account',
                'sales_account',
                'vat_account',
                'cost_of_sales_account',
            )
        }),
    )

# --------------------------------------------------
# فواتير المبيعات

class SalesInvoiceItemInline(admin.TabularInline):
    model = SalesInvoiceItem
    form = SalesInvoiceItemForm
    list_display = ('invoice', 'product', 'quantity', 'unit_price')
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'tax_rate',
              'total_before_tax', 'tax_amount', 'total_with_tax')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return []


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'date', 'customer','total_with_tax_value', 'is_posted', 'posting_button','pdf_button')


    readonly_fields = ['number','journal_entry', 'is_posted']
    inlines = [SalesInvoiceItemInline]

    fieldsets = (
        (None, {
            'fields': ('number', 'date', 'customer', 'warehouse', 'sales_rep','journal_entry', 'is_posted'),
        }),
        ('إجماليات الفاتورة 💰', {
            'fields': (('total_before_tax_value', 'total_tax_value', 'total_with_tax_value'),),
            'classes': ('invoice-totals-box',),
        }),
    )

    class Media:
        css = {
            'all': ['sales/css/sales_invoice_custom.css'],
        }
        js = ['js/invoice_items_auto_calc.js']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
        form.instance.save()

    def get_total_with_tax(self, obj):
        return obj.total_with_tax_value or 0
    get_total_with_tax.short_description = 'الإجمالي شامل الضريبة'

    def get_readonly_fields(self, request, obj=None):
        base_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_posted:
            return base_fields + [f.name for f in self.model._meta.fields]
        return base_fields



    def pdf_button(self, obj):
        url = reverse('sales:invoice_pdf', args=[obj.id])  # ✅ استخدم namespace هنا
        return format_html('<a class="button" href="{}">📄 طباعة PDF</a>', url)

    pdf_button.short_description = 'طباعة PDF'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:invoice_id>/post/', self.admin_site.admin_view(self.post_invoice), name='salesinvoice-post'),
            path('<int:invoice_id>/unpost/', self.admin_site.admin_view(self.unpost_invoice), name='salesinvoice-unpost'),
        ]
        return custom_urls + urls

    def post_invoice(self, request, invoice_id):
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        try:
            invoice.post_invoice()
            self.message_user(request, "✔ تم ترحيل الفاتورة بنجاح", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", messages.ERROR)
        return redirect(f'../../{invoice_id}/change/')

    def unpost_invoice(self, request, invoice_id):
        invoice = get_object_or_404(SalesInvoice, id=invoice_id)
        try:
            invoice.unpost_invoice()
            self.message_user(request, "❎ تم إلغاء ترحيل الفاتورة", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"⚠️ خطأ أثناء الإلغاء: {str(e)}", messages.ERROR)
        return redirect(f'../../{invoice_id}/change/')

    def posting_button(self, obj):
        if obj.is_posted:
            return format_html(
                '<a class="button" style="background:red;color:white;" href="{}">❌ إلغاء الترحيل</a>',
                reverse('admin:salesinvoice-unpost', args=[obj.pk])
            )
        return format_html(
            '<a class="button" style="background:green;color:white;" href="{}">✔ ترحيل</a>',
            reverse('admin:salesinvoice-post', args=[obj.pk])
        )
    posting_button.short_description = "الإجراء"

    def change_view(self, request, object_id, form_url='', extra_context=None):
        invoice = get_object_or_404(SalesInvoice, id=object_id)
        extra_context = extra_context or {}
        extra_context['show_totals_footer'] = True

        if invoice.is_posted:
            extra_context['custom_button'] = format_html(
                '<div style="margin:10px 0;"><a class="button" style="background:red;color:white;" href="../unpost/">❌ إلغاء الترحيل</a></div>'
            )
            extra_context.update({
                'show_save': False, 'show_save_and_continue': False,
                'show_save_and_add_another': False, 'show_delete': False,
            })
        else:
            extra_context['custom_button'] = format_html(
                '<div style="margin:10px 0;"><a class="button" style="background:green;color:white;" href="../post/">✔ ترحيل الفاتورة</a></div>'
            )

        return super().change_view(request, object_id, form_url, extra_context=extra_context)


# --------------------------------------------------
# مردودات المبيعات

class SalesReturnItemInline(admin.TabularInline):
    model = SalesReturnItem
    form = SalesReturnItemForm
    extra = 1
    fields = ('product', 'quantity', 'price', 'tax_rate',
              'total_before_tax', 'tax_amount', 'total_with_tax')
    readonly_fields = []

    def has_add_permission(self, request, obj=None):
        return not obj.is_posted if obj else True

    def has_change_permission(self, request, obj=None):
        return not obj.is_posted if obj else True

    def has_delete_permission(self, request, obj=None):
        return not obj.is_posted if obj else True


@admin.register(SalesReturn)
class SalesReturnAdmin(admin.ModelAdmin):
    list_display = ['number', 'customer', 'date', 'get_total_with_tax', 'is_posted', 'posting_button','print_pdf_button_ru']
    readonly_fields = ['number','journal_entry', 'is_posted']
    inlines = [SalesReturnItemInline]

    fieldsets = (
        (None, {
            'fields': ('number', 'date', 'customer', 'warehouse', 'sales_rep','journal_entry', 'is_posted'),
        }),
        ('إجماليات المرتجعات 💰', {
            'fields': (('total_before_tax_value', 'total_tax_value', 'total_with_tax_value'),),
            'classes': ('invoice-totals-box',),
        }),
    )

    def get_total_with_tax(self, obj):
        return obj.total_with_tax_value
    get_total_with_tax.short_description = "الإجمالي شامل الضريبة"


    class Media:
        css = {
            'all': ['sales/css/sales_invoice_custom.css'],
        }
        js = ['js/return_sales_invoice_totals.js','sales/js/return_sales_invoice_auto_calc.js']  # ✅ تأكد من وجود الملف الجديد


    def get_readonly_fields(self, request, obj=None):
        base = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_posted:
            return list(set(base + [f.name for f in self.model._meta.fields]))
        return base

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:return_id>/post/', self.admin_site.admin_view(self.post_return), name='salesreturn-post'),
            path('<int:return_id>/unpost/', self.admin_site.admin_view(self.unpost_return), name='salesreturn-unpost'),
        ]
        return custom + urls


    def print_pdf_button_ru(self, obj):
        url = reverse('sales:sales_return_invoice_pdf', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">📄 طباعة PDF</a>', url)

    print_pdf_button_ru.short_description = "طباعة PDF"


    def post_return(self, request, return_id):
        ret = get_object_or_404(SalesReturn, id=return_id)
        try:
            ret.post_return()
            self.message_user(request, "✔ تم ترحيل المردود بنجاح", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", messages.ERROR)
        return redirect(f'../../{return_id}/change/')

    def unpost_return(self, request, return_id):
        ret = get_object_or_404(SalesReturn, id=return_id)
        try:
            ret.unpost_return()
            self.message_user(request, "❎ تم إلغاء الترحيل بنجاح", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"⚠️ خطأ أثناء الإلغاء: {str(e)}", messages.ERROR)
        return redirect(f'../../{return_id}/change/')

    def posting_button(self, obj):
        if not obj.pk:
            return "-"
        if obj.is_posted:
            return format_html(
                '<a class="button" style="background:red;color:white;" href="{}">❌ إلغاء الترحيل</a>',
                reverse('admin:salesreturn-unpost', args=[obj.pk])
            )
        return format_html(
            '<a class="button" style="background:green;color:white;" href="{}">✔ ترحيل</a>',
            reverse('admin:salesreturn-post', args=[obj.pk])
        )
    posting_button.short_description = "الإجراء"



# --------------------------------------------------
# سداد العملاء

# admin.py
# admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import CustomerPayment
from .forms import CustomerPaymentForm

@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    form = CustomerPaymentForm

    list_display = ['number', 'customer', 'date', 'invoice', 'amount', 'linked_journal_entry_display']
    search_fields = ['customer__name']
    list_filter = ['date']
    readonly_fields = ['number', 'linked_journal_entry_display']

    def linked_journal_entry_display(self, obj):
        if obj.journal_entry:
            url = reverse('admin:accounts_journalentry_change', args=[obj.journal_entry.id])
            return format_html('<a href="{}" target="_blank">📘 {}</a>', url, obj.journal_entry.number)
        return "—"
    linked_journal_entry_display.short_description = "رقم القيد المحاسبي"

    class Media:
        js = [
            'js/customer_payment.js',
        ]




###########################################################################



#--------------------------------------------------------------------------------------------

# sales/admin.py
from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class SalesReportsFakeModel(models.Model):
    class Meta:
        managed = False  # لا يُنشئ جدول في قاعدة البيانات
        app_label = 'sales'
        verbose_name = "📊 تقارير المبيعات"
        verbose_name_plural = "📊 تقارير المبيعات"

    def __str__(self):
        return "📊 تقارير المبيعات"

@admin.register(SalesReportsFakeModel)
class SalesReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/sales/reports/')
    



    
from django.contrib import admin
from .models import SalesRepresentative, CommissionSlab

class CommissionSlabInline(admin.TabularInline):
    model = CommissionSlab
    extra = 1  # عدد الصفوف الفارغة الإضافية
    min_num = 0
    verbose_name = "شريحة عمولة"
    verbose_name_plural = "شرائح العمولة"

@admin.register(SalesRepresentative)
class SalesRepresentativeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'commission_type', 'fixed_commission_percent']
    list_filter = ['commission_type']
    search_fields = ['code', 'name']
    inlines = [CommissionSlabInline]


#@admin.register(CommissionSlab)
class CommissionSlabAdmin(admin.ModelAdmin):
    list_display = ['representative', 'min_amount', 'max_amount', 'commission_percent']
    list_filter = ['representative']
    search_fields = ['representative__name']

