from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class CashFlowActivity(models.TextChoices):
    OPERATING = 'operating', 'الأنشطة التشغيلية'
    INVESTING = 'investing', 'الأنشطة الاستثمارية'
    FINANCING = 'financing', 'الأنشطة التمويلية'
# ------------------------------------------------------------
class AccountGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("اسم المجموعة"))
    activity_type = models.CharField(
        max_length=20,
        choices=CashFlowActivity.choices,
        null=True,
        blank=True,
        verbose_name=_("نوع النشاط في التدفقات النقدية")
    )

    class Meta:
        verbose_name = "مجموعة الحساب"
        verbose_name_plural = "مجموعات الحسابات"



    def __str__(self):
        return self.name

class FinancialStatement(models.TextChoices):
    ASSETS = 'assets', _("الأصول")
    LIABILITIES = 'liabilities', _("الخصوم")
    EQUITY = 'equity', _("حقوق الملكية")
    REVENUE = 'revenue', _("الإيرادات")
    EXPENSES = 'expenses', _("المصروفات")


# ------------------------------------------------------------
class Mapping(models.Model):
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name = "التبويب"
        verbose_name_plural = "التبويبات"

    def __str__(self):
        return self.name


class SubMapping(models.Model):
    mapping = models.ForeignKey(Mapping, on_delete=models.CASCADE, related_name='sub_mappings')
    name = models.CharField(max_length=100)


    class Meta:
        verbose_name = "تبويب فرعي"
        verbose_name_plural = "التبويبات الفرعية"


    def __str__(self):
        return f"{self.name} ({self.mapping.name})"

# models.py

class AccountDirection(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name=_("الكود"))
    name = models.CharField(max_length=255, verbose_name=_("اسم التصنيف"))

    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "تصنيف الحساب"
        verbose_name_plural = "تصنيفات الحسابات"

# ------------------------------------------------------------

# accounts/models.py

class FinancialStatementType(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name="الرمز")
    name = models.CharField(max_length=100, verbose_name="الاسم")

    class Meta:
        verbose_name = "نوع القوائم المالية"
        verbose_name_plural = "أنواع القوائم المالية"

    def __str__(self):
        return f"{self.name}"

# ------------------------------------------------------------
class Account(models.Model):
    code = models.CharField(max_length=20, unique=True, verbose_name=_("كود الحساب"))
    name = models.CharField(max_length=255, verbose_name=_("اسم الحساب"))
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("الحساب الأب"))
    level = models.PositiveIntegerField(verbose_name=_("مستوى الحساب"))
    group = models.ForeignKey(AccountGroup, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("مجموعة التدفقات النقدية"))
    direction = models.ForeignKey(
        'AccountDirection',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("التصنيف الداخلي")
    )
    sub_mapping = models.ForeignKey(SubMapping, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("Sub-Mapping"))
    statement_type = models.ForeignKey(
        'FinancialStatementType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="نوع الحساب (القائمة المالية)"
    )


    class Meta:
        verbose_name = "الحساب"
        verbose_name_plural = "الحسابات"



    def __str__(self):
        return f"{self.code} - {self.name}"
    
    @property
    def is_leaf(self):
        return self.level == 3

    @property
    def can_be_used_in_entries(self):
        return self.is_leaf

    @property
    def children(self):
        return Account.objects.filter(parent=self).order_by('code')

# ------------------------------------------------------------
from django.utils import timezone 

from django.utils import timezone
from django.contrib.contenttypes.models import ContentType


class OpeningBalance(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    posted = models.BooleanField(default=False, verbose_name="تم الترحيل")


    class Meta:
        verbose_name = "رصيد افتتاحي"
        verbose_name_plural = "الأرصدة الافتتاحية"



    def __str__(self):
        return f"أرصدة افتتاحية #{self.id}"

    def post(self):
        if self.posted:
            return

        journal = JournalEntry.objects.create(
            date=timezone.datetime(timezone.now().year, 1, 1).date(),
            is_auto=True,
            description=f"قيد الأرصدة الافتتاحية #{self.id}",
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id,
        )

        for item in self.items.all():
            if item.debit > 0:
                JournalEntryLine.objects.create(
                    journal_entry=journal,
                    account=item.account,
                    debit=item.debit,
                    credit=0,
                    description="رصيد افتتاحي"
                )
            elif item.credit > 0:
                JournalEntryLine.objects.create(
                    journal_entry=journal,
                    account=item.account,
                    debit=0,
                    credit=item.credit,
                    description="رصيد افتتاحي"
                )

        self.posted = True
        self.save()

    def unpost(self):
        if not self.posted:
            return

        # حذف القيد المرتبط

        content_type = ContentType.objects.get_for_model(self)
        JournalEntry.objects.filter(content_type=content_type, object_id=self.id).delete()

        self.posted = False
        self.save()

class OpeningBalanceItem(models.Model):
    opening_balance = models.ForeignKey(OpeningBalance, related_name='items', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)
    debit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        unique_together = ('opening_balance', 'account')

    def __str__(self):
        return f"{self.account} - {self.debit} / {self.credit}"


# ------------------------------------------------------------
class JournalEntry(models.Model):
    number = models.CharField(max_length=20, unique=True, editable=False)
    date = models.DateField()
    notes = models.CharField(max_length=300, blank=True, null=True)
    is_auto = models.BooleanField(default=False, verbose_name="قيد أوتوماتيكي")
    description = models.CharField(max_length=300, blank=True, null=True)
    reference = models.CharField(max_length=100, null=True, blank=True)

    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    production_order = models.ForeignKey(
        'manufacturing.ProductionOrder',
        on_delete=models.CASCADE,  # ✅ هذا يجعل الحذف تلقائيًا
        null=True,
        blank=True,
        related_name='journal_entries'
    )



    class Meta:
        verbose_name = "قيد اليومية"
        verbose_name_plural = "قيود اليومية"




    def __str__(self):
        return f"{self.number} - {self.date}"

    def save(self, *args, **kwargs):
        if not self.number:
            prefix = 'AUTO' if self.is_auto else 'JE'
            last_entry = JournalEntry.objects.filter(number__startswith=prefix).order_by('id').last()
            if last_entry:
                last_number = int(last_entry.number.split('-')[1])
                self.number = f"{prefix}-{last_number + 1:06d}"
            else:
                self.number = f"{prefix}-000001"
        super().save(*args, **kwargs)

from django.db import models
from accounts.models import JournalEntry, Account

class JournalEntryLine(models.Model):
    journal_entry = models.ForeignKey(
        JournalEntry,
        related_name='lines',
        on_delete=models.CASCADE,
        verbose_name="القيد المحاسبي"
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        verbose_name="الحساب"
    )
    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="مدين"
    )
    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="دائن"
    )
    description = models.CharField(
        max_length=300,
        blank=True,
        null=True,
        verbose_name="البيان"
    )




    class Meta:
        verbose_name = "تفصيل قيد"
        verbose_name_plural = "تفاصيل القيود"
        ordering = ['id']

    def __str__(self):
        return f"{self.account} - مدين {self.debit} / دائن {self.credit}"
################################################################################################
