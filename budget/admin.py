from django.contrib import admin
from .models import Budget, BudgetEntry
from accounts.models import Account



from django import forms
from .models import BudgetEntry

class BudgetEntryInlineForm(forms.ModelForm):
    class Meta:
        model = BudgetEntry
        fields = '__all__'
        widgets = {
            month: forms.NumberInput(attrs={'style': 'width: 60px;', 'step': '0.01'})
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # تأكد أن هناك حساب مرتبط
        account = self.instance.account if self.instance.pk else None
        if account and account.level != 4:
            for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun',
                          'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                self.fields[month].disabled = True


from django.forms.models import BaseInlineFormSet
class BudgetEntryInlineFormSet(BaseInlineFormSet):
    def save(self, commit=True):
        instances = super().save(commit=False)
        budget = self.instance

        if commit:
            for entry in instances:
                entry.save()

            from accounts.models import Account
            from budget.models import BudgetEntry

            # اجلب حسابات المستوى 4 المستخدمة فعلاً في هذه الموازنة
            level_4_accounts = Account.objects.filter(level=4)
            used_acc_ids = BudgetEntry.objects.filter(budget=budget, account__in=level_4_accounts).values_list('account', flat=True)
            used_accounts = Account.objects.filter(id__in=used_acc_ids)

            # جهّز قائمة بالآباء من المستوى 1-3
            parents_by_level = {1: set(), 2: set(), 3: set()}
            for acc in used_accounts:
                parent = acc.parent
                while parent:
                    if parent.level in parents_by_level:
                        parents_by_level[parent.level].add(parent)
                    parent = parent.parent

            # نفّذ التجميع للمستويات 3 ← 2 ← 1
            for level in [3, 2, 1]:
                for acc in sorted(parents_by_level[level], key=lambda a: a.code):
                    children = Account.objects.filter(parent=acc)
                    totals = {m: 0 for m in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']}
                    for child in children:
                        entry = BudgetEntry.objects.filter(budget=budget, account=child).first()
                        if entry:
                            for month in totals:
                                totals[month] += getattr(entry, month) or 0

                    # أنشئ أو حدّث الإدخال
                    parent_entry, _ = BudgetEntry.objects.get_or_create(budget=budget, account=acc)
                    for month in totals:
                        setattr(parent_entry, month, totals[month])
                    parent_entry.save()

        return instances




class BudgetEntryInline(admin.TabularInline):
    model = BudgetEntry
    form = BudgetEntryInlineForm
    formset = BudgetEntryInlineFormSet
    extra = 0

    class Media:
        js = ('js/auto_sum.js',)


    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "account":
            kwargs["queryset"] = Account.objects.filter(level=4).order_by('code')
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('account').order_by('account__code')

    # عرض كود واسم الحساب
    def account_code(self, obj):
        return obj.account.code
    account_code.short_description = "كود الحساب"

    def account_name(self, obj):
        return obj.account.name
    account_name.short_description = "اسم الحساب"

    readonly_fields = ('account_code', 'account_name')  # عرض فقط، بدون تعديل
    fields = ('account_code', 'account_name',
              'jan', 'feb', 'mar', 'apr', 'may', 'jun',
              'jul', 'aug', 'sep', 'oct', 'nov', 'dec')


#@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('year', 'name', 'created_by', 'created_at')
    inlines = [BudgetEntryInline]

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        super().save_model(request, obj, form, change)

        if is_new:
            from accounts.models import Account
            from accounts.models import AccountDirection  # إضافة هذا السطر
            from .models import BudgetEntry

            # جلب فقط حسابات المستوى الرابع من نوع "قائمة الدخل" (IS)
            income_type = AccountDirection.objects.get(code='IS')
            accounts = Account.objects.filter(level=4, direction=income_type).order_by('code')

            for account in accounts:
                BudgetEntry.objects.create(
                    budget=obj,
                    account=account,
                    jan=0, feb=0, mar=0, apr=0, may=0, jun=0,
                    jul=0, aug=0, sep=0, oct=0, nov=0, dec=0
                )
