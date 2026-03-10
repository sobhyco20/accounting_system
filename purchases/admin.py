from decimal import Decimal
from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect, get_object_or_404
from django.template.response import TemplateResponse
from django.utils.dateparse import parse_date
from .forms import PurchaseInvoiceItemForm, PurchaseReturnItemForm,SupplierPaymentForm

from .models import (
    SupplierGroup, Supplier, PurchaseInvoice, PurchaseInvoiceItem,
    PurchaseReturn, PurchaseReturnItem, SupplierPayment
)

from io import BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse, HttpResponseRedirect
from inventory.models import Product


# --------------------------------------------------
# مجموعات الموردين والموردين

@admin.register(SupplierGroup)
class SupplierGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'account']
    search_fields = ['name']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'group', 'opening_credit', 'phone']
    list_filter = ['group']
    search_fields = ['code', 'name', 'phone']
    autocomplete_fields = ['account','inventory_account', 'vat_account', 'inventory_account']


# --------------------------------------------------
# فواتير المشتريات
# admin.py - المشتريات

from django.contrib import admin, messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect, get_object_or_404

from .models import PurchaseInvoice, PurchaseInvoiceItem
from .forms import PurchaseInvoiceItemForm


class PurchaseInvoiceItemInline(admin.TabularInline):
    model = PurchaseInvoiceItem
    form = PurchaseInvoiceItemForm
    extra = 1
    fields = ('product', 'quantity', 'unit_price', 'tax_rate',
              'total_before_tax', 'tax_amount', 'total_with_tax')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return []

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return list(self.readonly_fields)


@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ['number', 'supplier', 'date', 'get_total_with_tax', 'is_posted', 'posting_button','print_pdf_button']
    readonly_fields = ['number','journal_entry', 'is_posted']
    inlines = [PurchaseInvoiceItemInline]
    search_fields = ['number', 'supplier__name']

    fieldsets = (
        (None, {
            'fields': ('number', 'date', 'supplier', 'warehouse','sales_rep', 'journal_entry', 'is_posted'),
        }),
        ('إجماليات الفاتورة', {
            'fields': (('total_before_tax_value', 'total_tax_value', 'total_with_tax_value'),),
            'classes': ('invoice-totals-box',),
        }),
    )

    class Media:
        css = {
            'all': ['css/pur_invoice_custom.css'],
        }
        js = ['js/pur_invoice_items_auto_calc.js']  

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

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_delete_permission(request, obj)


    def print_pdf_button(self, obj):
        url = reverse('purchases:purchase_invoice_pdf', args=[obj.pk])  # تأكد أن اسم الـ namespace والتسمية صحيحة
        return format_html('<a class="button" href="{}" target="_blank">🖨 طباعة</a>', url)
    print_pdf_button.short_description = "طباعة PDF"


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:invoice_id>/post/', self.admin_site.admin_view(self.post_invoice), name='purchaseinvoice-post'),
            path('<int:invoice_id>/unpost/', self.admin_site.admin_view(self.unpost_invoice), name='purchaseinvoice-unpost'),
        ]
        return custom_urls + urls

    def post_invoice(self, request, invoice_id):
        invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)
        try:
            invoice.post_invoice()
            self.message_user(request, "✔ تم ترحيل الفاتورة بنجاح", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", messages.ERROR)
        return redirect(f'../../{invoice_id}/change/')

    def unpost_invoice(self, request, invoice_id):
        invoice = get_object_or_404(PurchaseInvoice, id=invoice_id)
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
                reverse('admin:purchaseinvoice-unpost', args=[obj.pk])
            )
        return format_html(
            '<a class="button" style="background:green;color:white;" href="{}">✔ ترحيل</a>',
            reverse('admin:purchaseinvoice-post', args=[obj.pk])
        )
    posting_button.short_description = "الإجراء"

    def change_view(self, request, object_id, form_url='', extra_context=None):
        invoice = get_object_or_404(PurchaseInvoice, id=object_id)
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
# مردودات المشتريات

class PurchaseReturnItemInline(admin.TabularInline):
    model = PurchaseReturnItem
    form = PurchaseReturnItemForm
    extra = 1
    fields = ('product', 'quantity', 'price', 'tax_rate',
              'total_before_tax', 'tax_amount', 'total_with_tax')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return list(self.readonly_fields)

    def has_add_permission(self, request, obj=None):
        return True  # اسمح بالإضافة دائماً

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True


@admin.register(PurchaseReturn)
class PurchaseReturnAdmin(admin.ModelAdmin):
    list_display = ['number', 'supplier', 'date', 'get_total_with_tax', 'is_posted', 'posting_button','print_pdf_button']
    readonly_fields = ['number', 'journal_entry', 'is_posted']
    inlines = [PurchaseReturnItemInline]

    fieldsets = (
        ('بيانات المرتجع', {
            'fields': (
                'number',
                'date',
                'supplier',
                'warehouse',
                'sales_rep',
                'original_invoice',
            ),
        }),
        ('إجماليات المرتجع', {
            'fields': (
                ('total_before_tax_value', 'total_tax_value', 'total_with_tax_value'),
            ),
            'classes': ('invoice-totals-box',),
        }),
        ('الترحيل والمراجعة', {
            'fields': (
                'journal_entry',
                'is_posted',
            ),
            'classes': ('collapse',),
        }),
    )


    class Media:
        css = {
            'all': ['css/pur_invoice_custom.css'],
        }
        js = ['js/re_pur_invoice_items_auto_calc.js']

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            instance.save()
        formset.save_m2m()
        form.instance.save()

    def get_total_with_tax(self, obj):
        return obj.total_with_tax_value
    get_total_with_tax.short_description = "الإجمالي شامل الضريبة"

    def get_readonly_fields(self, request, obj=None):
        base_fields = list(super().get_readonly_fields(request, obj))
        if obj and obj.is_posted:
            return base_fields + [f.name for f in self.model._meta.fields]
        return base_fields
    

    def print_pdf_button(self, obj):
        url = reverse('purchases:purchase_return_invoice_pdf', args=[obj.pk])
        return format_html('<a class="button" href="{}" target="_blank">🖨 طباعة</a>', url)
    print_pdf_button.short_description = "طباعة PDF"



    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_delete_permission(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:return_id>/post/', self.admin_site.admin_view(self.post_return), name='purchasereturn-post'),
            path('<int:return_id>/unpost/', self.admin_site.admin_view(self.unpost_return), name='purchasereturn-unpost'),
        ]
        return custom + urls

    def post_return(self, request, return_id):
        ret = get_object_or_404(PurchaseReturn, id=return_id)
        try:
            ret.post_return()
            self.message_user(request, "✔ تم ترحيل المردود بنجاح", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", messages.ERROR)
        return redirect(f'../../{return_id}/change/')

    def unpost_return(self, request, return_id):
        ret = get_object_or_404(PurchaseReturn, id=return_id)
        try:
            ret.unpost_return()
            self.message_user(request, "❎ تم إلغاء ترحيل المردود", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"⚠️ خطأ أثناء الإلغاء: {str(e)}", messages.ERROR)
        return redirect(f'../../{return_id}/change/')

    def posting_button(self, obj):
        if not obj.pk:
            return "-"
        if obj.is_posted:
            return format_html(
                '<a class="button" style="background:red;color:white;" href="{}">❌ إلغاء الترحيل</a>',
                reverse('admin:purchasereturn-unpost', args=[obj.pk])
            )
        return format_html(
            '<a class="button" style="background:green;color:white;" href="{}">✔ ترحيل</a>',
            reverse('admin:purchasereturn-post', args=[obj.pk])
        )
    posting_button.short_description = "الإجراء"

    def change_view(self, request, object_id, form_url='', extra_context=None):
        ret = get_object_or_404(PurchaseReturn, id=object_id)
        extra_context = extra_context or {}
        extra_context['show_totals_footer'] = True

        if ret.is_posted:
            extra_context['custom_button'] = format_html(
                '<div style="margin:10px 0;"><a class="button" style="background:red;color:white;" href="../unpost/">❌ إلغاء الترحيل</a></div>'
            )
            extra_context.update({
                'show_save': False, 'show_save_and_continue': False,
                'show_save_and_add_another': False, 'show_delete': False,
            })
        else:
            extra_context['custom_button'] = format_html(
                '<div style="margin:10px 0;"><a class="button" style="background:green;color:white;" href="../post/">✔ ترحيل المردود</a></div>'
            )

        return super().change_view(request, object_id, form_url, extra_context=extra_context)



# --------------------------------------------------
# سداد الموردين
@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    form = SupplierPaymentForm

    list_display = ['number', 'supplier', 'date', 'invoice', 'amount', 'linked_journal_entry_display']
    search_fields = ['supplier__name']
    list_filter = ['date']
    readonly_fields = ['number', 'linked_journal_entry_display']

    def linked_journal_entry_display(self, obj):
        if obj.journal_entry:
            url = reverse('admin:accounts_journalentry_change', args=[obj.journal_entry.id])
            return format_html('<a href="{}" target="_blank">📘 {}</a>', url, obj.journal_entry.number)
        return "—"
    linked_journal_entry_display.short_description = "رقم القيد المحاسبي"

    class Media:
        js = ['js/supplier_payment.js']



#-------------------------------------------------------------------------------------------------------

from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class PurchaseReportsFakeModel(models.Model):
    class Meta:
        managed = False
        app_label = 'purchases'
        verbose_name = "🧾 تقارير المشتريات"
        verbose_name_plural = "🧾 تقارير المشتريات"

    def __str__(self):
        return "🧾 تقارير المشتريات"

@admin.register(PurchaseReportsFakeModel)
class PurchaseReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/purchases/reports/')

