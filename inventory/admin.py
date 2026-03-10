from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.urls import path, reverse
from django.utils.html import format_html
from accounts.models import JournalEntry, JournalEntryLine
from django.contrib.contenttypes.models import ContentType 

from .models import (
    Warehouse,
    Unit,
    Product,
    OpeningStockBalance,
    OpeningStockItem,
    StockTransaction,
    StockTransactionItem,
    InventoryReportsDummy,
    InventoryBalanceDummy,
)


########################################################################################################
class ScrapTransactionAdmin(admin.ModelAdmin):
    def get_readonly_fields(self, request, obj=None):
        if obj and obj.production_order:
            # جعل كل الحقول للعرض فقط
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.production_order:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.production_order:
            return False
        return super().has_change_permission(request, obj)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(notes__icontains='خردة')

################################################################################################################

# المستودعات
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'region', 'warehouse_type', 'inventory_account']
    search_fields = ['code', 'name']
    list_filter = ['warehouse_type']

# الوحدات
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_base', 'parent_unit', 'conversion_factor']
    list_filter = ['is_base']

# الأصناف
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'product_type', 'large_unit', 'small_unit', 'conversion_factor']
    list_filter = ['product_type']
    search_fields = ['code', 'name']

# تفاصيل حركة المخزون

class StockTransactionItemInline(admin.TabularInline):
    model = StockTransactionItem
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return not obj or not obj.is_posted

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return []


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ["date", "warehouse", "transaction_type", "is_posted", "posting_status"]
    inlines = [StockTransactionItemInline]
    change_form_template = "admin/inventory/stocktransaction/change_form.html"
    actions = ["action_post_transactions", "action_unpost_transactions"]



    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_delete_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_change_permission(request, obj)


    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/post/', self.admin_site.admin_view(self.post_transaction), name='stocktransaction-post'),
            path('<int:pk>/unpost/', self.admin_site.admin_view(self.unpost_transaction), name='stocktransaction-unpost'),
        ]
        return custom_urls + urls

    def post_transaction(self, request, pk):
        obj = self.get_object(request, pk)
        try:
            obj.post_transaction()
            self.message_user(request, "✅ تم ترحيل الحركة بنجاح.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ فشل الترحيل: {e}", messages.ERROR)
        return redirect(f"../../{pk}/change/")

    def unpost_transaction(self, request, pk):
        obj = self.get_object(request, pk)
        try:
            obj.unpost_transaction()
            self.message_user(request, "✅ تم إلغاء الترحيل بنجاح.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ فشل إلغاء الترحيل: {e}", messages.ERROR)
        return redirect(f"../../{pk}/change/")

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        context['show_post'] = obj and not obj.is_posted and not obj.sales_invoice and not obj.sales_return and not obj.production_order
        context['show_unpost'] = obj and obj.is_posted and not obj.sales_invoice and not obj.sales_return and not obj.production_order
        context['disable_save'] = obj and (obj.is_posted or obj.sales_invoice or obj.sales_return or obj.production_order)
        return super().render_change_form(request, context, add, change, form_url, obj)

    def posting_status(self, obj):
        if obj.sales_invoice or obj.sales_return:
            return "🔒 منشأة من فاتورة"
        if obj.is_posted:
            url = reverse('admin:stocktransaction-unpost', args=[obj.pk])
            return format_html('<a class="button" href="{}">إلغاء الترحيل</a>', url)
        else:
            url = reverse('admin:stocktransaction-post', args=[obj.pk])
            return format_html('<a class="button" href="{}">ترحيل</a>', url)

    posting_status.short_description = "الترحيل"

    def action_post_transactions(self, request, queryset):
        count = 0
        for obj in queryset:
            if not obj.is_posted and not obj.sales_invoice and not obj.sales_return:
                try:
                    obj.post_transaction()
                    count += 1
                except Exception as e:
                    self.message_user(request, f"❌ {obj} فشل في الترحيل: {e}", level=messages.ERROR)
        self.message_user(request, f"✅ تم ترحيل {count} حركة بنجاح.", level=messages.SUCCESS)

    action_post_transactions.short_description = "🔁 ترحيل الحركات المحددة"

    def action_unpost_transactions(self, request, queryset):
        count = 0
        for obj in queryset:
            if obj.is_posted and not obj.sales_invoice and not obj.sales_return:
                try:
                    obj.unpost_transaction()
                    count += 1
                except Exception as e:
                    self.message_user(request, f"❌ {obj} فشل في إلغاء الترحيل: {e}", level=messages.ERROR)
        self.message_user(request, f"✅ تم إلغاء ترحيل {count} حركة.", level=messages.SUCCESS)

    action_unpost_transactions.short_description = "↩️ إلغاء ترحيل الحركات المحددة"


###############################################################################

from django.contrib import admin, messages
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import OpeningStockBalance, OpeningStockItem, StockTransaction, StockTransactionItem


class OpeningStockItemInline(admin.TabularInline):
    model = OpeningStockItem
    extra = 1
    fields = ['product', 'quantity', 'unit', 'unit_cost', 'total_cost']
    readonly_fields = ['total_cost']

    def total_cost(self, obj):
        if obj.quantity and obj.unit_cost:
            return obj.quantity * obj.unit_cost
        return 0
    total_cost.short_description = "إجمالي التكلفة"

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return self.fields
        return self.readonly_fields

    def has_add_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.is_posted:
            return False
        return super().has_delete_permission(request, obj)


@admin.register(OpeningStockBalance)
class OpeningStockBalanceAdmin(admin.ModelAdmin):
    list_display = ['id', 'warehouse', 'date', 'is_posted', 'post_button']
    inlines = [OpeningStockItemInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_posted:
            return [f.name for f in self.model._meta.fields]
        return []

    def has_delete_permission(self, request, obj=None):
        return not obj or not obj.is_posted

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        extra_context = extra_context or {}
        if obj and obj.is_posted:
            extra_context['show_save'] = False
            extra_context['show_delete'] = False
            extra_context['show_save_and_continue'] = False
            extra_context['show_save_and_add_another'] = False
        return super().change_view(request, object_id, form_url, extra_context)

    def post_button(self, obj):
        if not obj.is_posted:
            url = reverse('admin:post-opening-stock', args=[obj.pk])
            return format_html(f'<a class="button" href="{url}">ترحيل</a>')
        else:
            url = reverse('admin:unpost-opening-stock', args=[obj.pk])
            return format_html(f'<a class="button" style="color:red;" href="{url}">إلغاء الترحيل</a>')
    post_button.short_description = "الترحيل"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/post/', self.admin_site.admin_view(self.post_balance), name='post-opening-stock'),
            path('<int:pk>/unpost/', self.admin_site.admin_view(self.unpost_balance), name='unpost-opening-stock'),
        ]
        return custom_urls + urls

    def post_balance(self, request, pk):
        balance = get_object_or_404(OpeningStockBalance, pk=pk)

        if balance.is_posted:
            self.message_user(request, "تم ترحيل هذا الرصيد مسبقًا.", messages.WARNING)
            return redirect('admin:inventory_openingstockbalance_change', pk)

        inventory_account = balance.warehouse.inventory_account

        if not inventory_account:
            self.message_user(request, "لا يوجد حساب مخزون مرتبط بهذا المستودع.", messages.ERROR)
            return redirect('admin:inventory_openingstockbalance_change', pk)

        tx = StockTransaction.objects.create(
            date=balance.date,
            warehouse=balance.warehouse,
            transaction_type='opening_balance',
            related_account=inventory_account
        )

        for item in balance.items.all():
            StockTransactionItem.objects.create(
                transaction=tx,
                product=item.product,
                quantity=item.quantity,
                unit=item.unit,
                cost=item.unit_cost
            )

        balance.is_posted = True
        balance.save()

        self.message_user(request, "تم ترحيل رصيد أول المدة بنجاح.", messages.SUCCESS)
        return redirect('admin:inventory_openingstockbalance_change', pk)

    def unpost_balance(self, request, pk):
        balance = get_object_or_404(OpeningStockBalance, pk=pk)

        if not balance.is_posted:
            self.message_user(request, "هذا الرصيد غير مرحل بعد.", messages.WARNING)
            return redirect('admin:inventory_openingstockbalance_change', pk)

        StockTransaction.objects.filter(
            transaction_type='opening_balance',
            warehouse=balance.warehouse,
            related_account=balance.warehouse.inventory_account
        ).delete()

        balance.is_posted = False
        balance.save()

        self.message_user(request, "تم إلغاء ترحيل رصيد أول المدة.", messages.SUCCESS)
        return redirect('admin:inventory_openingstockbalance_change', pk)

###############################################################################

from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class InventoryReportsFakeModel(models.Model):
    class Meta:
        managed = False  # لا يتم إنشاء جدول فعلي في قاعدة البيانات
        app_label = 'inventory'
        verbose_name = "📦 تقارير المستودعات"
        verbose_name_plural = "📦 تقارير المستودعات"

    def __str__(self):
        return "📦 تقارير المستودعات"

@admin.register(InventoryReportsFakeModel)
class InventoryReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/inventory/reports/')


