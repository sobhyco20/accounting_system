from django.db import models
from accounts.models import Account, JournalEntry, JournalEntryLine
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from decimal import Decimal
from hr.models import Employee



class TreasuryBox(models.Model):
    BOX_TYPES = (
        ('cash', 'صندوق'),
        ('bank', 'بنك'),
    )

    name = models.CharField(max_length=100)
    box_type = models.CharField(max_length=10, choices=BOX_TYPES)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name="الحساب المرتبط")
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name="رصيد أول المدة")


    class Meta:
        verbose_name = "صندوق"
        verbose_name_plural = "الصناديق"


    def __str__(self):
        return self.name




User = get_user_model()

class TreasuryVoucher(models.Model):
    VOUCHER_TYPES = (
        ('receipt', 'سند قبض'),
        ('payment', 'سند صرف'),
    )

    code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    voucher_type = models.CharField(max_length=10, choices=VOUCHER_TYPES)
    date = models.DateField()
    box = models.ForeignKey('TreasuryBox', on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=300, blank=True, null=True)
    account = models.ForeignKey('accounts.Account', on_delete=models.PROTECT, related_name='counterparty_account')
    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True)

    responsible = models.ForeignKey(
        Employee,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="الموظف المسؤول"
    )


    class Meta:
        verbose_name = "سند خزنة"
        verbose_name_plural = "سندات الخزنة"


    def __str__(self):
        resp = f"{self.responsible.employee_code} - {self.responsible.full_name}" if self.responsible else "غير محدد"
        return f"{self.code} - {resp}"


    def save(self, *args, **kwargs):
        creating = self.pk is None
        old_journal = self.journal_entry if not creating else None

        # توليد الكود تلقائيًا عند الإنشاء
        if creating and not self.code:
            prefix = 'rec' if self.voucher_type == 'receipt' else 'pay'
            last = TreasuryVoucher.objects.filter(voucher_type=self.voucher_type, code__startswith=prefix).order_by('id').last()
            last_number = 0
            if last and last.code:
                try:
                    last_number = int(last.code.split('-')[-1])
                except:
                    pass
            new_number = last_number + 1
            self.code = f"{prefix}-{str(new_number).zfill(6)}"

        # حفظ أولي لحجز pk
        super().save(*args, **kwargs)

        # حذف القيد السابق إذا كان موجودًا
        if old_journal:
            old_journal.lines.all().delete()
            old_journal.delete()

        # إنشاء القيد الجديد
        journal = JournalEntry.objects.create(
            number=f"TREASURY-{self.id}",
            date=self.date,
            notes=self.description or "",
            content_type=ContentType.objects.get_for_model(self.__class__),
            object_id=self.id,
            is_auto=True,
        )

        if self.voucher_type == 'receipt':
            # قيد قبض: مدين الصندوق، دائن الطرف الآخر
            JournalEntryLine.objects.create(journal_entry=journal, account=self.box.account, debit=self.amount)
            JournalEntryLine.objects.create(journal_entry=journal, account=self.account, credit=self.amount)
        else:
            # قيد صرف: مدين الطرف الآخر، دائن الصندوق
            JournalEntryLine.objects.create(journal_entry=journal, account=self.account, debit=self.amount)
            JournalEntryLine.objects.create(journal_entry=journal, account=self.box.account, credit=self.amount)

        self.journal_entry = journal
        super().save(update_fields=['journal_entry'])

    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.lines.all().delete()
            self.journal_entry.delete()
        super().delete(*args, **kwargs)



class BankAccount(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم البنك")
    account_number = models.CharField(max_length=50, verbose_name="رقم الحساب")

    def __str__(self):
        return self.name



from django.db import models

class TreasuryReportsFakeModel(models.Model):
    class Meta:
        managed = False  # لن يُنشئ جدول فعلي في قاعدة البيانات
        app_label = 'treasury'
        verbose_name = "💰 تقارير الصندوق"
        verbose_name_plural = "💰 تقارير الصندوق"

    def __str__(self):
        return "💰 تقارير الصندوق"
