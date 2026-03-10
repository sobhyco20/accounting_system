from decimal import Decimal
from django.db import models
from django.contrib.contenttypes.models import ContentType

from accounts.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Warehouse, Product, Unit, WarehouseOrder, WarehouseOrderItem
from purchases.models import PurchaseInvoice
from treasury.models import TreasuryBox, TreasuryVoucher
from treasury.models import TreasuryBox, BankAccount






class CustomerGroup(models.Model):
    name = models.CharField(max_length=100)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name="الحساب المالي")
    class Meta:
        verbose_name = "مجموعة عملاء"
        verbose_name_plural = "مجموعات العملاء"

    def __str__(self):
        return self.name


class Customer(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50, verbose_name="الرقم الضريبي", blank=True, null=True)
    group = models.ForeignKey(CustomerGroup, on_delete=models.CASCADE)
    opening_debit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    opening_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=50, blank=True, null=True)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='customers_account', verbose_name="حساب العميل")
    sales_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='customers_sales_account', verbose_name="حساب المبيعات")
    vat_account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='customers_vat_account', verbose_name="حساب الضريبة")
    cost_of_sales_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True, related_name='cost_of_sales_customers', verbose_name="حساب تكلفة البضاعة المباعة")
    

    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"



    def save(self, *args, **kwargs):
        if not self.code:
            last_customer = Customer.objects.order_by('-id').first()
            if last_customer and last_customer.code:
                try:
                    last_number = int(last_customer.code.split('-')[-1])
                except ValueError:
                    last_number = 0
            else:
                last_number = 0
            new_number = last_number + 1
            self.code = f"CUS-{new_number:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
    
#------------------------------------------------------------------------------------------------------------------------------------------------

class SalesInvoice(models.Model):
    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    date = models.DateField()
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    sales_rep = models.ForeignKey('sales.SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)

    journal_entry = models.OneToOneField(
        JournalEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name='sales_invoice'
    )
    is_posted = models.BooleanField(default=False)

    total_before_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    

    class Meta:
        verbose_name = "فاتورة مبيعات"
        verbose_name_plural = "فاتورة مبيعات"


    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # توليد الرقم التلقائي فقط إذا كانت الفاتورة جديدة ولم يُعط لها رقم
        if is_new and not self.number:
            last_invoice = SalesInvoice.objects.order_by('-id').first()
            if last_invoice and last_invoice.number:
                try:
                    last_number = int(last_invoice.number.split('-')[-1])
                except ValueError:
                    last_number = 0
            else:
                last_number = 0
            self.number = f"S.INVO-{last_number + 1:04d}"

        super().save(*args, **kwargs)

        # بعد الحفظ الأول نستطيع احتساب المجاميع لأنه أصبح يوجد self.items.all()
        if is_new:
            total_before = sum(item.total_before_tax for item in self.items.all())
            total_tax = sum(item.tax_amount for item in self.items.all())
            total_with = total_before + total_tax

            self.total_before_tax_value = total_before
            self.total_tax_value = total_tax
            self.total_with_tax_value = total_with

            super().save(update_fields=['total_before_tax_value', 'total_tax_value', 'total_with_tax_value'])

    def __str__(self):
        return f"{self.number}"



    def post_invoice(self):
        from inventory.models import StockTransaction, StockTransactionItem  # ✅ استيراد داخلي لتجنب الدوران

        if self.is_posted:
            raise Exception("⚠️ الفاتورة مرحّلة مسبقًا.")

        # التأكد من إعداد الحسابات
        if not self.customer.account or not self.customer.sales_account \
                or not self.customer.vat_account or not self.warehouse.inventory_account \
                or not self.customer.cost_of_sales_account:
            raise Exception("⚠️ تأكد من إعداد جميع الحسابات اللازمة.")

        # حذف القيد القديم إن وجد
        if self.journal_entry:
            self.journal_entry.delete()

        # حذف الحركات وأمر الصرف السابقين
        StockTransaction.objects.filter(sales_invoice=self).delete()
        WarehouseOrder.objects.filter(reference=f"فاتورة مبيعات رقم {self.number}").delete()

        # حساب الإجماليات
        total_before = sum(item.total_before_tax for item in self.items.all())
        total_tax = sum(item.tax_amount for item in self.items.all())
        total_total = total_before + total_tax

        # إنشاء القيد المحاسبي
        entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"قيد آلي ناتج عن فاتورة مبيعات رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(SalesInvoice),
            object_id=self.id
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.customer.account,
            debit=total_total,
            credit=0,
            description="فاتورة مبيعات"
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.customer.sales_account,
            debit=0,
            credit=total_before,
            description="قيمة الأصناف"
        )
        if total_tax > 0:
            JournalEntryLine.objects.create(
                journal_entry=entry,
                account=self.customer.vat_account,
                debit=0,
                credit=total_tax,
                description="ضريبة المبيعات"
            )

        # إنشاء أمر صرف موحد
        order = WarehouseOrder.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            type='out',
            reference=f"فاتورة مبيعات رقم {self.number}",
            notes="أمر صرف بضاعة لفاتورة المبيعات"
        )

        # إنشاء حركة المخزون (الرأس)
        stock_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            transaction_type='out',
            related_account=self.customer.sales_account,
            sales_invoice=self,
            notes=f"صرف بضاعة لفاتورة مبيعات رقم {self.number}"
        )

        cost_total = Decimal('0.00')
        for item in self.items.all():
            unit = item.product.base_unit or item.product.small_unit

            WarehouseOrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit=unit
            )

            StockTransactionItem.objects.create(
                transaction=stock_tx,
                product=item.product,
                quantity=item.quantity,
                unit=unit,
                cost=item.unit_price
            )

            cost_total += (item.unit_price or Decimal('0.00')) * (item.quantity or Decimal('0.00'))

        # قيد تكلفة البضاعة المباعة
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.customer.cost_of_sales_account,
            debit=cost_total,
            credit=0,
            description="تكلفة البضاعة المباعة"
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.warehouse.inventory_account,
            debit=0,
            credit=cost_total,
            description="من حساب المخزون"
        )

        self.journal_entry = entry
        self.is_posted = True
        self.save(update_fields=["journal_entry", "is_posted"])

    def unpost_invoice(self):
        from inventory.models import StockTransaction  # ✅ استيراد مؤجل أيضًا

        if self.journal_entry:
            self.journal_entry.delete()

        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()
        StockTransaction.objects.filter(sales_invoice=self).delete()

        self.journal_entry = None
        self.is_posted = False
        self.save(update_fields=["journal_entry", "is_posted"])

#-----------------------------------------------------------------------------------------------------------------


class SalesInvoiceItem(models.Model):
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    total_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_tax = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        qty = self.quantity or Decimal('0')
        price = self.unit_price or Decimal('0')
        rate = self.tax_rate or Decimal('0')

        self.total_before_tax = qty * price
        self.tax_amount = self.total_before_tax * rate / Decimal('100')
        self.total_with_tax = self.total_before_tax + self.tax_amount

        super().save(*args, **kwargs)

#------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------------------------------------------------------

class CustomerPayment(models.Model):
    number = models.CharField(max_length=20, unique=True, verbose_name='رقم السداد')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, verbose_name='العميل')
    date = models.DateField(verbose_name='تاريخ السداد')
    treasury_box = models.ForeignKey(
        TreasuryBox,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الصندوق / البنك'
    )
    invoice = models.ForeignKey(SalesInvoice, on_delete=models.CASCADE, verbose_name='رقم الفاتورة')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, editable=False)


    class Meta:
        verbose_name = "دفعة عميل"
        verbose_name_plural = "دفعات العملاء"



    def __str__(self):
        return f"سداد {self.customer} - {self.amount}"

    @property
    def invoice_remaining_before_payment(self):
        total_paid = CustomerPayment.objects.filter(invoice=self.invoice).exclude(pk=self.pk).aggregate(total=models.Sum('amount'))['total'] or 0
        total_invoice = self.invoice.total_with_tax_value
        return total_invoice - total_paid

    def save(self, *args, **kwargs):
        creating = self.pk is None

        # توليد رقم السند تلقائياً
        if not self.number:
            last_payment = CustomerPayment.objects.order_by('-id').first()
            if last_payment and last_payment.number:
                try:
                    last_number = int(last_payment.number.replace('pay-', ''))
                except:
                    last_number = 0
                self.number = f"pay-{str(last_number + 1).zfill(5)}"
            else:
                self.number = "pay-00001"

        super().save(*args, **kwargs)

        # حذف القيد القديم إن وجد
        if self.journal_entry:
            self.journal_entry.delete()
            self.journal_entry = None
            super().save(update_fields=['journal_entry'])

        # التحقق من الصندوق/البنك
        if not self.treasury_box:
            raise ValueError("يجب اختيار صندوق أو بنك.")
        if not self.treasury_box.account:
            raise ValueError("يجب تحديد الحساب المرتبط بالصندوق/البنك.")

        # إنشاء القيد

        debit_account = self.treasury_box.account
        credit_account = self.customer.account

        box_type_label = "نقدًا" if self.treasury_box.box_type == 'cash' else "تحويل بنكي"

        entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"سند قبض من العميل {self.customer.name} رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(CustomerPayment),
            object_id=self.id
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=debit_account,
            debit=self.amount,
            credit=0,
            description=f"سند قبض {box_type_label} من العميل رقم {self.number} | {self.customer.name}"
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=credit_account,
            debit=0,
            credit=self.amount,
            description=f"سداد من العميل رقم {self.number} | {self.customer.name}"
        )

        self.journal_entry = entry
        super().save(update_fields=['journal_entry'])

    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.delete()
        super().delete(*args, **kwargs)


#-----------------------------------------------------------------------------------------------

class SalesReportsDummy(models.Model):
    class Meta:
        managed = False
        verbose_name = "تقارير المبيعات"
        verbose_name_plural = "تقارير المبيعات"


def create_sales_invoice_entry(invoice):
    entry = JournalEntry.objects.create(
        date=invoice.date,
        notes=f"قيد فاتورة مبيعات رقم {invoice.number}",
        is_auto=True,
    )

    JournalEntryLine.objects.create(journal_entry=entry, account=invoice.customer.account, debit=invoice.total_after_tax(), credit=0, description="إجمالي الفاتورة على العميل")
    JournalEntryLine.objects.create(journal_entry=entry, account=invoice.customer.sales_account, debit=0, credit=invoice.total_before_tax(), description="قيمة الأصناف")
    if invoice.tax_amount() > 0:
        JournalEntryLine.objects.create(journal_entry=entry, account=invoice.customer.vat_account, debit=0, credit=invoice.tax_amount(), description="ضريبة القيمة المضافة")

    invoice.journal_entry = entry
    invoice.save(update_fields=["journal_entry"])

#------------------------------------------------------------------------------------------------------------


class SalesReturn(models.Model):
    number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    date = models.DateField()
    customer = models.ForeignKey('sales.Customer', on_delete=models.CASCADE)
    warehouse = models.ForeignKey('inventory.Warehouse', on_delete=models.CASCADE)
    sales_rep = models.ForeignKey('sales.SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)

    original_invoice = models.ForeignKey('sales.SalesInvoice', on_delete=models.SET_NULL, null=True, blank=True)
    journal_entry = models.OneToOneField('accounts.JournalEntry', null=True, blank=True, on_delete=models.SET_NULL)
    is_posted = models.BooleanField(default=False)

    total_before_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_with_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))


    class Meta:
        verbose_name = "فاتورة مردودات مبيعات"
        verbose_name_plural = "فاتورة مردودات مبيعات"


    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # أول حفظ، نحفظ بدون رقم للحصول على ID
        super().save(*args, **kwargs)

        # بعد الحفظ الأول يتم توليد الرقم إذا لم يكن موجود
        if is_new and not self.number:
            self.number = f"RS.INVO-{str(self.pk).zfill(4)}"
            super().save(update_fields=['number'])

        # ثم نحسب الإجماليات إذا أردت بعد ذلك
        total_before = sum(item.total_before_tax for item in self.details.all())
        total_tax = sum(item.tax_amount for item in self.details.all())
        total_with_tax = sum(item.total_with_tax for item in self.details.all())

        self.total_before_tax_value = total_before
        self.total_tax_value = total_tax
        self.total_with_tax_value = total_with_tax

        super().save(update_fields=['total_before_tax_value', 'total_tax_value', 'total_with_tax_value'])

    def __str__(self):
        return self.number



    def post_return(self):
        from inventory.models import StockTransaction, StockTransactionItem

        if self.is_posted:
            raise Exception("⚠️ تم ترحيل مردود المبيعات مسبقًا.")
        if not self.customer.account or not self.customer.sales_account or not self.customer.vat_account:
            raise Exception("⚠️ تأكد من إعداد الحسابات المرتبطة بالعميل.")
        if not self.warehouse.inventory_account:
            raise Exception("⚠️ تأكد من إعداد حساب المخزون للمستودع.")
        if not self.customer.cost_of_sales_account:
            raise Exception("⚠️ تأكد من إعداد حساب تكلفة البضاعة للعميل.")

        # حذف القديم
        if self.journal_entry:
            self.journal_entry.delete()
        StockTransaction.objects.filter(sales_return=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()

        # إنشاء قيد اليومية
        journal_entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"قيد آلي ناتج عن مردودات مبيعات رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(SalesReturn),
            object_id=self.id
        )

        # قيود اليومية للمردود
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.customer.sales_account,
            debit=self.total_before_tax_value,
            credit=0,
            description="مردودات مبيعات"
        )
        if self.total_tax_value > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=self.customer.vat_account,
                debit=self.total_tax_value,
                credit=0,
                description="ضريبة مردود المبيعات"
            )
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.customer.account,
            debit=0,
            credit=self.total_with_tax_value,
            description="إرجاع للعميل"
        )

        # إنشاء أمر المستودع وحركات الجرد
        order = WarehouseOrder.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            type='in',
            reference=f"مردود مبيعات رقم {self.number}",
            notes="إرجاع تلقائي من مردود المبيعات"
        )
        stock_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            transaction_type='in',
            related_account=self.customer.sales_account,
            sales_return=self,
            notes=f"إرجاع من مردود مبيعات رقم {self.number}"
        )

        cost_total = Decimal('0.00')
        for item in self.details.all():
            unit = item.product.base_unit or item.product.small_unit
            WarehouseOrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                unit=unit
            )
            StockTransactionItem.objects.create(
                transaction=stock_tx,
                product=item.product,
                quantity=item.quantity,
                unit=unit,
                cost=item.price
            )
            cost_total += (item.price or Decimal('0.00')) * (item.quantity or Decimal('0.00'))

        # قيود تكلفة البضاعة
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.warehouse.inventory_account,
            debit=cost_total,
            credit=0,
            description="إرجاع للمخزون"
        )
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.customer.cost_of_sales_account,
            debit=0,
            credit=cost_total,
            description="عكس تكلفة البضاعة المباعة"
        )

        self.journal_entry = journal_entry
        self.is_posted = True
        self.save(update_fields=["journal_entry", "is_posted"])


    def unpost_return(self):
        from inventory.models import StockTransaction
        JournalEntry.objects.filter(content_type=ContentType.objects.get_for_model(SalesReturn), object_id=self.id).delete()
        StockTransaction.objects.filter(sales_return=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()
        self.journal_entry = None
        self.is_posted = False
        self.save(update_fields=["journal_entry", "is_posted"])

    def delete(self, *args, **kwargs):
        if self.is_posted:
            self.unpost_return()
        super().delete(*args, **kwargs)




class SalesReturnItem(models.Model):
    sales_return = models.ForeignKey(SalesReturn, related_name="details", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))

    total_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_with_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    def save(self, *args, **kwargs):
        qty = self.quantity or Decimal('0')
        price = self.price or Decimal('0')
        rate = self.tax_rate or Decimal('0')

        self.total_before_tax = qty * price
        self.tax_amount = self.total_before_tax * rate / Decimal('100')
        self.total_with_tax = self.total_before_tax + self.tax_amount

        super().save(*args, **kwargs)
#------------------------------------------------------------------------------------------------

# models.py
from django.db import models

class SalesRepresentative(models.Model):

    COMMISSION_TYPE_CHOICES = [
        ('fixed_percent', 'نسبة ثابتة من المبيعات'),
        ('slabs', 'شرائح حسب حجم المبيعات'),
    ]
    code = models.CharField(max_length=20, verbose_name="كود المندوب", blank=True, null=True)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    commission_type = models.CharField(
        max_length=20,
        choices=COMMISSION_TYPE_CHOICES,
        default='fixed_percent',
        verbose_name="نوع العمولة"
    )
    fixed_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name="نسبة العمولة الثابتة",
        help_text="مثلاً 5 تعني 5% من المبيعات"
    )

    class Meta:
        verbose_name = "المندوبين"
        verbose_name_plural = "المندوبيـــن"

    def __str__(self):
        return self.name

class CommissionSlab(models.Model):
    representative = models.ForeignKey(SalesRepresentative, on_delete=models.CASCADE, related_name='commission_slabs')
    min_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="من مبيعات")
    max_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="إلى مبيعات")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="نسبة العمولة")

    class Meta:
        verbose_name = "شريحة عمولة"
        verbose_name_plural = "شرائح العمولة"
        ordering = ['min_amount']

    def __str__(self):
        return f"{self.representative.name} - من {self.min_amount} إلى {self.max_amount} => {self.commission_percent}%"



def calculate_commission(rep, total_sales):
    details = []
    total_commission = Decimal('0.00')

    if rep.commission_type == 'fixed_percent':
        percent = rep.fixed_commission_percent or 0
        total_commission = (total_sales * percent / 100).quantize(Decimal('0.01'))
        details.append({
            "type": "نسبة ثابتة",
            "percentage": percent,
            "amount": total_commission,
        })

    elif rep.commission_type == 'slabs':
        # اجلب كل الشرائح الخاصة بالمندوب المرتبة من الأصغر للأكبر
        slabs = rep.commission_slabs.order_by('min_amount')
        for slab in slabs:
            if slab.min_amount <= total_sales <= slab.max_amount:
                percent = slab.commission_percent
                commission = (total_sales * percent / 100).quantize(Decimal('0.01'))
                total_commission = commission
                details.append({
                    "tier": f"{slab.min_amount} - {slab.max_amount}",
                    "percentage": percent,
                    "amount": commission,
                })
                break  # توقف عند أول شريحة تنطبق

    return total_commission, details
