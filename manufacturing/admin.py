from django.contrib import admin
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

from .models import (
    BillOfMaterials, BillOfMaterialsComponent, AppliedCostToBOM,
    ProductionOrder, ProductionMaterialMovement,
    ProductionOrderComponent, ProductionOrderExpense,DefaultComponent
)

from .forms import BOMComponentForm, BillOfMaterialsForm
from django.urls import path
########################################################################################################################

class BillOfMaterialsComponentInline(admin.TabularInline):
    model = BillOfMaterialsComponent
    form = BOMComponentForm
    extra = 1
    fields = ('component', 'quantity', 'unit_cost', 'calculated_total')
    readonly_fields = ('calculated_total',)
    verbose_name = "مكون"
    verbose_name_plural = "مكونات المنتج"

    def calculated_total(self, obj):
        if obj.pk:
            return obj.total_cost()
        return 0
    calculated_total.short_description = "الإجمالي"


class AppliedCostToBOMInline(admin.TabularInline):
    model = AppliedCostToBOM
    extra = 1
    fields = ('expense', 'quantity', 'value', 'total_display')
    readonly_fields = ('total_display',)
    verbose_name = "مصروف"
    verbose_name_plural = "المصروفات المحملة"

    def total_display(self, obj):
        if obj.pk:
            return round(obj.total, 2)
        return 0

    total_display.short_description = "الإجمالي"


#@admin.register(BillOfMaterials)
class BillOfMaterialsAdmin(admin.ModelAdmin):
    form = BillOfMaterialsForm
    inlines = [BillOfMaterialsComponentInline, AppliedCostToBOMInline]

    readonly_fields = (
        'total_component_cost_display',
        'total_expense_cost_display',
        'total_cost_display',
        'unit_cost_display',
    )

    fieldsets = (
        (None, {
            'fields': ('product', 'quantity_produced'),
        }),
        ('إجماليات مكونات المنتج 💰', {
            'fields': (
                ('total_component_cost_display', 'total_expense_cost_display'),
                ('total_cost_display', 'unit_cost_display'),
            ),
            'classes': ('invoice-totals-box',),
        }),
    )


    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)

        if request.GET.get('update_bom') == '1' and obj:
            # حذف المكونات القديمة (اختياري)
            obj.components.all().delete()

            # استيراد المكونات الافتراضية
            defaults = DefaultComponent.objects.filter(product=obj.product)
            for default in defaults:
                BillOfMaterialsComponent.objects.create(
                    bom=obj,
                    component=default.component,
                    quantity=default.quantity
                )

            self.message_user(request, "تم تحميل المكونات من المنتج بنجاح.")
            return redirect(f"{request.path}")  # إعادة تحميل الصفحة بدون ?update_bom

        return super().change_view(request, object_id, form_url, extra_context)
    class Media:
        js = ['js/bom_auto_calc.js','js/bom_component.js',]   

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        super().save_model(request, obj, form, change)

        if is_new:
            obj.components.all().delete()
            for default in obj.product.default_bom_components.all():
                BillOfMaterialsComponent.objects.create(
                    bom=obj,
                    component=default.component,
                    quantity=default.quantity,
                    unit_cost=default.unit_cost,
                )

        obj.update_totals()
        obj.save()

    def save_formset(self, request, form, formset, change):
        instances = formset.save()  # حفظ العناصر
        form.instance.update_totals()  # حساب الإجماليات بعد تأكد وجود pk
        form.instance.save()

    def total_component_cost_display(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<div id="total_component_cost_display">{}</div>', obj.total_component_cost)
    total_component_cost_display.short_description = "إجمالي تكلفة المكونات"

    def total_expense_cost_display(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<div id="total_expense_cost_display">{}</div>', obj.total_expense_cost)
    total_expense_cost_display.short_description = "إجمالي المصروفات المحملة"

    def total_cost_display(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<div id="total_cost_display">{}</div>', obj.total_cost)
    total_cost_display.short_description = "التكلفة الإجمالية"

    def unit_cost_display(self, obj):
        if not obj.pk:
            return "-"
        return format_html('<div id="unit_cost_display">{}</div>', obj.unit_cost)
    unit_cost_display.short_description = "تكلفة الوحدة"

########################################################################################################################################


class ProductionExpenseAdmin(admin.ModelAdmin):
    list_display = ['name', 'account', 'is_active']
    search_fields = ['name']
    autocomplete_fields = ['account']

########################################################################################################################################


class ProductionOrderComponentInline(admin.TabularInline):
    model = ProductionOrderComponent
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_cost', 'total_cost_display')
    fields = ('product', 'quantity', 'unit_cost', 'total_cost_display')

    def total_cost_display(self, obj):
        return obj.total_cost
    total_cost_display.short_description = "الإجمالي"


class ProductionOrderExpenseInline(admin.TabularInline):
    model = ProductionOrderExpense
    extra = 0
    readonly_fields = ('expense', 'quantity', 'value', 'total_display')
    fields = ('expense', 'quantity', 'value', 'total_display')

    def total_display(self, obj):
        return obj.total
    total_display.short_description = "الإجمالي"



#@admin.register(ProductionOrder)
class ProductionOrderAdmin(admin.ModelAdmin):
    inlines = [ProductionOrderComponentInline, ProductionOrderExpenseInline]
    change_form_template = "admin/manufacturing/productionorder/production_order_change_form.html"
    
    list_display = ('code', 'product', 'quantity', 'status_display')
    readonly_fields = ('code',)

    actions = ['issue_materials', 'close_production_order']


    def get_readonly_fields(self, request, obj=None):
        base = super().get_readonly_fields(request, obj)
        if obj and obj.is_posted:
            return base + tuple(f.name for f in self.model._meta.fields)
        return base

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not obj.is_posted:
            return True  # السماح بالحذف فقط إذا لم يكن مرحلًا
        return super().has_delete_permission(request, obj)


    def has_change_permission(self, request, obj=None):
        if obj and obj.is_posted and request.path.endswith("/change/"):
            # السماح بتغيير فقط عبر زر "إلغاء الترحيل"
            return request.POST.get('_unpost') == '1'
        return super().has_change_permission(request, obj=obj)

    @admin.display(description='الحالة')
    def status_display(self, obj):
        if obj.is_posted:
            return format_html(
                f"<b style='color:green;'>مرحّل</b> "
                f"<a href='/admin/manufacturing/productionorder/{obj.id}/unpost/' style='margin-right:10px;'>"
                f"<button style='color:red;'>إلغاء الترحيل</button></a>"
            )
        else:
            return format_html("<b style='color:red;'>غير مرحّل</b>")


    def issue_materials(self, request, queryset):
        for order in queryset:
            if order.is_materials_issued:
                self.message_user(request, f"تم صرف المواد مسبقًا لأمر {order.code}", messages.WARNING)
                continue
            order.issue_materials_only()
            order.is_materials_issued = True
            order.save()
            self.message_user(request, f"تم صرف المواد لأمر {order.code}", messages.SUCCESS)
    issue_materials.short_description = "صرف المواد الخام"

    def close_production_order(self, request, queryset):
        for order in queryset:
            if order.is_closed:
                self.message_user(request, f"تم إغلاق أمر {order.code} مسبقًا", messages.WARNING)
                continue
            if not order.is_materials_issued:
                self.message_user(request, f"يجب صرف المواد أولاً قبل إغلاق أمر {order.code}", messages.ERROR)
                continue
            order.close_order()
            order.is_closed = True
            order.status = 'done'
            order.save()
            self.message_user(request, f"تم إغلاق أمر {order.code} بنجاح", messages.SUCCESS)
    close_production_order.short_description = "إغلاق أمر الإنتاج"


    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        
        if request.method == 'POST':
            if "_post_order" in request.POST:
                obj.post_order()
                self.message_user(request, "تم ترحيل أمر الإنتاج بنجاح ✅", messages.SUCCESS)
                return redirect(request.path)

            elif "_unpost_order" in request.POST:
                obj.unpost_order()
                self.message_user(request, "تم إلغاء ترحيل أمر الإنتاج ❌", messages.WARNING)
                return redirect(request.path)

        extra_context = extra_context or {}
        extra_context['show_post_button'] = obj and not obj.is_posted
        extra_context['show_unpost_button'] = obj and obj.is_posted
        return super().change_view(request, object_id, form_url, extra_context=extra_context)


    def get_readonly_fields(self, request, obj=None):
        base = super().get_readonly_fields(request, obj)
        if obj and obj.is_posted:
            return base + tuple(
                field.name for field in self.model._meta.fields if field.name not in ['id', 'status']
            )
        return base


    def response_add(self, request, obj, post_url_continue=None):
        if "_save_and_continue_editing_bom" in request.POST:
            url = reverse('admin:manufacturing_productionorder_change', args=[obj.pk])
            return HttpResponseRedirect(url)
        return super().response_add(request, obj, post_url_continue)

    def response_change(self, request, obj):
        if "_save_and_continue_editing_bom" in request.POST:
            return HttpResponseRedirect(f"/admin/manufacturing/productionorder/{obj.pk}/change/?update_bom=1")
        return super().response_change(request, obj)


    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        from inventory.models import Product  # عدل حسب مكان المنتج
        extra_context = extra_context or {}
        extra_context['component_choices'] = Product.objects.all()
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    class Media:
        js = ('js/production_order_auto_calc.js',)


    readonly_fields = ('code','total_component_cost_display', 'total_expense_cost_display', 'total_cost_display', 'unit_cost_display')

    fieldsets = (
        (None, {
            'fields': (
                ('code', 'product'),
                ('quantity', 'status'),
                ('start_date', 'end_date'),
                ('notes',),
            ),
        }),
        ('المستودعات المرتبطة', {
            'fields': (
                ('raw_material_warehouse', 'wip_warehouse'),
                ('finished_goods_warehouse', 'scrap_warehouse'),
            ),
        }),
        ('الإنتاج الفعلي', {
            'fields': (
                ('finished_quantity','scrap_quantity',),
                )
        }),
        ('الإجماليات', {
            'fields': (
                ('total_component_cost_display', 'total_expense_cost_display'),
                ('total_cost_display', 'unit_cost_display'),
            ),
        }),
    )




    def total_component_cost_display(self, obj):
        return obj.total_component_cost
    total_component_cost_display.short_description = "تكلفة المكونات"

    def total_expense_cost_display(self, obj):
        return obj.total_expense_cost
    total_expense_cost_display.short_description = "تكلفة المصاريف"

    def total_cost_display(self, obj):
        return obj.total_cost
    total_cost_display.short_description = "التكلفة الإجمالية"

    def unit_cost_display(self, obj):
        return obj.unit_cost
    unit_cost_display.short_description = "تكلفة الوحدة"

    # تحميل BOM عند الحفظ لأول مرة
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        # عند الحفظ لأول مرة
        if not change:
            try:
                bom = BillOfMaterials.objects.get(product=obj.product)
                # إنشاء المكونات
                for item in bom.components.all():
                    ProductionOrderComponent.objects.create(
                        order=obj,
                        product=item.component,
                        quantity=item.quantity * obj.quantity,
                        unit_cost=item.unit_cost
                    )
                # إنشاء المصاريف
                for exp in bom.expenses.all():
                    ProductionOrderExpense.objects.create(
                        order=obj,
                        expense=exp.expense,
                        quantity=exp.quantity * obj.quantity,
                        value=exp.value
                    )
            except BillOfMaterials.DoesNotExist:
                pass
        else:
            # إذا كان هناك تغيير في الكمية فقط، قم بتحديث التفاصيل
            if 'quantity' in form.changed_data:
                try:
                    bom = BillOfMaterials.objects.get(product=obj.product)
                    # تحديث المكونات
                    for item in bom.components.all():
                        component = ProductionOrderComponent.objects.filter(order=obj, product=item.component).first()
                        if component:
                            component.quantity = item.quantity * obj.quantity
                            component.save()
                    # تحديث المصاريف
                    for exp in bom.expenses.all():
                        expense = ProductionOrderExpense.objects.filter(order=obj, expense=exp.expense).first()
                        if expense:
                            expense.quantity = exp.quantity * obj.quantity
                            expense.save()
                except BillOfMaterials.DoesNotExist:
                    pass


    def delete_model(self, request, obj):
        if obj.is_posted:
            raise Exception("لا يمكن حذف أمر مرحّل. الرجاء إلغاء الترحيل أولاً.")
        obj.delete()


    def delete_queryset(self, request, queryset):
        for obj in queryset:
            try:
                if obj.is_posted:
                    obj.unpost_order()
            except Exception as e:
                self.message_user(request, f"خطأ عند إلغاء الترحيل: {e}", level='error')
            obj.delete()


    def unpost_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj:
            try:
                obj.unpost()
                messages.success(request, "تم إلغاء ترحيل أمر الإنتاج بنجاح.")
            except Exception as e:
                messages.error(request, f"خطأ: {e}")
        return redirect(f"/admin/manufacturing/productionorder/")

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/unpost/', self.admin_site.admin_view(self.unpost_view), name='productionorder-unpost'),
        ]
        return custom_urls + urls


####################################################################################################################
####################################################################################################################







#@admin.register(ProductionMaterialMovement)
class ProductionMaterialMovementAdmin(admin.ModelAdmin):
    list_display = ('order', 'movement_type', 'product', 'quantity', 'warehouse', 'date')
    list_filter = ['movement_type', 'warehouse']
    search_fields = ['product__name', 'order__code']
    date_hierarchy = 'date'

#####################################################################################################################
from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class ManufacturingReportsFakeModel(models.Model):
    class Meta:
        managed = False  # لا يتم إنشاء جدول في قاعدة البيانات
        app_label = 'manufacturing'
        verbose_name = "📊 تقارير التصنيع"
        verbose_name_plural = "📊 تقارير التصنيع"

    def __str__(self):
        return "📊 تقارير التصنيع"

#@admin.register(ManufacturingReportsFakeModel)
class ManufacturingReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/manufacturing/reports/')
