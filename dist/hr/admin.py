from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import Department, Division, Employee, PayrollBatch, PayrollLine, PayrollAdjustmentHeader, PayrollAdjustmentLine,LeaveRequest

from .forms import LeaveRequestForm

class PayrollAdjustmentLineInline(admin.TabularInline):
    model = PayrollAdjustmentLine
    extra = 0
    readonly_fields = ['employee']


@admin.register(PayrollAdjustmentHeader)
class PayrollAdjustmentHeaderAdmin(admin.ModelAdmin):
    list_display = ['department', 'month', 'year']
    list_filter = ['department', 'year', 'month']
    inlines = [PayrollAdjustmentLineInline]

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)
        if is_new:
            obj.create_lines_for_employees()


class PayrollLineInline(admin.TabularInline):
    model = PayrollLine
    extra = 0


@admin.register(PayrollBatch)
class PayrollBatchAdmin(admin.ModelAdmin):
    inlines = [PayrollLineInline]
    change_form_template = "admin/hr/payrollbatch/change_form.html"
    exclude = ['accrual_posted', 'payment_posted']

    fieldsets = (
        (None, {
            'fields': ('year', 'month', 'department')
        }),
        ('تفاصيل الرواتب', {
            'fields': (
                ('total_base_salary', 'total_allowances', 'total_bonuses'),
                ('total_deductions', 'total_net_salary'),
            )
        }),
    )

    list_display = ('department', 'month', 'year', 'total_net_salary')
    list_filter = ('department', 'year', 'month')
    search_fields = ('department__name',)
    ordering = ('-year', '-month')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/generate-lines/',
                self.admin_site.admin_view(self.generate_lines_view),
                name='payroll_generate_lines',
            ),
            path(
                '<int:pk>/post-accrual/',
                self.admin_site.admin_view(self.post_accrual),
                name='payroll_post_accrual',
            ),
            path(
                '<int:pk>/post-payment/',
                self.admin_site.admin_view(self.post_payment),
                name='payroll_post_payment',
            ),
            path(
                '<int:pk>/unpost-all/',
                self.admin_site.admin_view(self.unpost_all),
                name='payroll_unpost_all',
            ),
        ]
        return custom_urls + urls

    def generate_lines_view(self, request, pk):
        batch = self.get_object(request, pk)
        if batch:
            try:
                batch.generate_lines_from_adjustments()
                messages.success(request, "✅ تم توليد تفاصيل الرواتب من التعديلات.")
            except Exception as e:
                messages.error(request, f"❌ خطأ أثناء التوليد: {e}")
        else:
            messages.error(request, "لم يتم العثور على المسير.")
        return redirect(reverse('admin:hr_payrollbatch_change', args=[pk]))

    def post_accrual(self, request, pk):
        obj = self.get_object(request, pk)
        try:
            obj.post_accrual()
            self.message_user(request, f"✅ تم ترحيل قيد الاستحقاق لمسير {obj.month:02d}/{obj.year}.")
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {e}", level=messages.ERROR)
        return redirect(f"../../{pk}/change/")

    def post_payment(self, request, pk):
        obj = self.get_object(request, pk)
        try:
            obj.post_payment()
            self.message_user(request, f"✅ تم ترحيل قيد الصرف لمسير {obj.month:02d}/{obj.year}.")
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {e}", level=messages.ERROR)
        return redirect(f"../../{pk}/change/")

    def unpost_all(self, request, pk):
        obj = self.get_object(request, pk)
        obj.unpost_all()
        self.message_user(request, f"🚫 تم إلغاء ترحيل القيود لمسير {obj.month:02d}/{obj.year}.", level=messages.WARNING)
        return redirect(f"../../{pk}/change/")

    def get_readonly_fields(self, request, obj=None):
        if obj and (obj.accrual_posted or obj.payment_posted):
            return [
                'month', 'year', 'department',
                'total_base_salary', 'total_allowances', 'total_bonuses',
                'total_deductions', 'total_net_salary',
            ]
        return []

    def save_model(self, request, obj, form, change):
        if obj.department:
            obj.payment_account = obj.department.payment_account
        super().save_model(request, obj, form, change)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ['name', 'department']
    list_filter = ['department']
    search_fields = ['name']


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = [
        'employee_code', 'full_name', 'department', 'division',
        'position_title', 'email', 'phone', 'hire_date',
        'base_salary', 'housing_allowance', 'transport_allowance',
        'other_allowances', 'bonuses', 'deductions', 'net_salary', 'is_active'
    ]
    list_filter = ['department', 'division', 'is_active']
    search_fields = ['employee_code', 'full_name', 'email', 'phone']
        
    @admin.display(description="الإجازات المستخدمة")
    def used_leave_days_display(self, obj):
        return obj.used_leave_days

    @admin.display(description="الرصيد المتبقي")
    def remaining_leave_days_display(self, obj):
        total = obj.employee.annual_leave_days
        used = obj.employee.remaining_leave_days()
        return total - used



@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'days', 'deduction_amount']
    list_filter = ['leave_type',  'start_date']
    search_fields = ['employee__full_name']
    readonly_fields = ['days', 'deduction_amount']
    form = LeaveRequestForm
        




from .models import LeaveReturn

@admin.register(LeaveReturn)
class LeaveReturnAdmin(admin.ModelAdmin):
    list_display = ['leave', 'return_date', 'created_at']
    search_fields = ['leave__employee__full_name']
    list_filter = ['return_date']


from django.contrib import admin
from .models import Advance, AdvanceInstallment

class AdvanceInstallmentInline(admin.TabularInline):
    model = AdvanceInstallment
    extra = 0
    readonly_fields = ['month', 'year', 'amount', 'is_paid']
    can_delete = False
    show_change_link = False

@admin.register(Advance)
class AdvanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'amount', 'start_month', 'start_year', 'installments_count', 'created_at']
    list_filter = ['start_year', 'start_month', 'employee__department']
    search_fields = ['employee__full_name', 'employee__employee_code']
    inlines = [AdvanceInstallmentInline]
    readonly_fields = ['created_at']

    def installments_count(self, obj):
        return obj.installments.count()
    installments_count.short_description = "عدد الأقساط"

#############################################################################################

from django.contrib import admin
from .models import EndOfServicePolicy

@admin.register(EndOfServicePolicy)
class EndOfServicePolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'first_years', 'reward_per_year_first', 'reward_per_year_after', 'percentage']
    search_fields = ['name', 'code']



#################################################################################################
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType

from .models import LeaveAllowance
from accounts.models import JournalEntry


@admin.register(LeaveAllowance)
class LeaveAllowanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'pay_date', 'total_amount', 'is_posted']
    readonly_fields = [
        'base_salary_amount', 'housing_amount', 'transport_amount',
        'other_allowances_amount', 'total_amount', 'is_posted',
        'post_button', 'unpost_button'
    ]

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.is_posted:
            # اجعل جميع الحقول مقفولة إذا تم الترحيل
            return [f.name for f in obj._meta.fields] + ['post_button', 'unpost_button']
        return fields

    def post_button(self, obj):
        if obj and obj.pk and not obj.is_posted:
            url = reverse('admin:leave_allowance_post', args=[obj.pk])
            return format_html(
                '<a class="button" style="color:green; font-weight:bold;" href="{}">📤 ترحيل القيد</a>',
                url
            )
        return ""
    post_button.short_description = "ترحيل القيد"

    def unpost_button(self, obj):
        if obj and obj.pk and obj.is_posted:
            url = reverse('admin:leave_allowance_unpost', args=[obj.pk])
            return format_html(
                '<a class="button" style="color:red; font-weight:bold;" href="{}">❌ إلغاء الترحيل</a>',
                url
            )
        return ""
    unpost_button.short_description = "إلغاء الترحيل"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('post/<int:pk>/', self.admin_site.admin_view(self.post_entry), name='leave_allowance_post'),
            path('unpost/<int:pk>/', self.admin_site.admin_view(self.unpost_entry), name='leave_allowance_unpost'),
        ]
        return custom_urls + urls

    def post_entry(self, request, pk):
        obj = LeaveAllowance.objects.get(pk=pk)
        try:
            obj.post_journal_entry()
            self.message_user(request, "✅ تم ترحيل القيد بنجاح", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", level=messages.ERROR)
        return redirect(f'../../{pk}/change/')

    def unpost_entry(self, request, pk):
        obj = LeaveAllowance.objects.get(pk=pk)
        if obj.is_posted:
            JournalEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.id
            ).delete()
            obj.is_posted = False
            obj.save()
            self.message_user(request, "❌ تم إلغاء الترحيل بنجاح", level=messages.SUCCESS)
        return redirect(f'../../{pk}/change/')



#####################################################################################################################
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.html import format_html
from django.contrib.contenttypes.models import ContentType
from .models import EndOfServiceReward
from accounts.models import JournalEntry


@admin.register(EndOfServiceReward)
class EndOfServiceRewardAdmin(admin.ModelAdmin):
    list_display = ['employee', 'reward_date', 'years', 'months', 'days', 'reward_amount', 'is_posted']
    readonly_fields = ['years', 'months', 'days', 'years_of_service', 'reward_amount', 'is_posted', 'post_button', 'unpost_button']
    list_filter = ['is_posted', 'reward_date']
    search_fields = ['employee__full_name']

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        if obj and obj.is_posted:
            return [f.name for f in obj._meta.fields] + ['post_button', 'unpost_button']
        return fields

    def post_button(self, obj):
        if obj and obj.pk and not obj.is_posted:
            url = reverse('admin:eos_reward_post', args=[obj.pk])
            return format_html(
                '<a class="button" style="color:green; font-weight:bold;" href="{}">📤 ترحيل القيد</a>',
                url
            )
        return ""
    post_button.short_description = "ترحيل القيد"

    def unpost_button(self, obj):
        if obj and obj.pk and obj.is_posted:
            url = reverse('admin:eos_reward_unpost', args=[obj.pk])
            return format_html(
                '<a class="button" style="color:red; font-weight:bold;" href="{}">❌ إلغاء الترحيل</a>',
                url
            )
        return ""
    unpost_button.short_description = "إلغاء الترحيل"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('post/<int:pk>/', self.admin_site.admin_view(self.post_entry), name='eos_reward_post'),
            path('unpost/<int:pk>/', self.admin_site.admin_view(self.unpost_entry), name='eos_reward_unpost'),
        ]
        return custom_urls + urls

    def post_entry(self, request, pk):
        obj = EndOfServiceReward.objects.get(pk=pk)
        try:
            obj.post_journal_entry()
            self.message_user(request, "✅ تم ترحيل القيد بنجاح", level=messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"❌ خطأ أثناء الترحيل: {str(e)}", level=messages.ERROR)
        return redirect(f'../../{pk}/change/')

    def unpost_entry(self, request, pk):
        obj = EndOfServiceReward.objects.get(pk=pk)
        if obj.is_posted:
            JournalEntry.objects.filter(
                content_type=ContentType.objects.get_for_model(obj),
                object_id=obj.id
            ).delete()
            obj.is_posted = False
            obj.save()
            self.message_user(request, "❌ تم إلغاء الترحيل بنجاح", level=messages.SUCCESS)
        return redirect(f'../../{pk}/change/')

####################################################################################################

from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class HRReportsFakeModel(models.Model):
    class Meta:
        managed = False
        app_label = 'hr'
        verbose_name = "📊 تقارير الموارد البشرية"
        verbose_name_plural = "📊 تقارير الموارد البشرية"

    def __str__(self):
        return "📊 تقارير الموارد البشرية"

@admin.register(HRReportsFakeModel)
class HRReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/hr/reports/')
