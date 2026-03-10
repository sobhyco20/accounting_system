from decimal import Decimal
from django.db import models
from django.contrib.contenttypes.models import ContentType
from accounts.models import Account, JournalEntry, JournalEntryLine
from inventory.models import Warehouse, Product, Unit, WarehouseOrder, WarehouseOrderItem


class SupplierGroup(models.Model):
    name = models.CharField(max_length=100)
    account = models.ForeignKey(Account, on_delete=models.CASCADE, verbose_name="الحساب المالي")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مجموعة موردين"
        verbose_name_plural = "مجموعات الموردين"

class Supplier(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    tax_number = models.CharField(max_length=50, verbose_name="الرقم الضريبي", blank=True, null=True)
    group = models.ForeignKey(SupplierGroup, on_delete=models.CASCADE)
    opening_debit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    opening_credit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    phone = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=50, blank=True, null=True)

    account = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name='suppliers_account',
        verbose_name="حساب المورد"
    )
    purchases_account = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name='suppliers_purchases_account',
        verbose_name="حساب المشتريات"
    )
    vat_account = models.ForeignKey(
        Account, on_delete=models.PROTECT,
        related_name='suppliers_vat_account',
        verbose_name="حساب الضريبة"
    )
    inventory_account = models.ForeignKey(  
        Account, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='supplier_inventory_accounts',
        verbose_name="حساب المخزون"
    )

    
    class Meta:
        verbose_name = "مورد"
        verbose_name_plural = "الموردون"


    def save(self, *args, **kwargs):
        if not self.code:
            last_supplier = Supplier.objects.all().order_by('-id').first()
            if last_supplier and last_supplier.code.startswith('SUP-'):
                last_code = int(last_supplier.code.split('-')[1])
                new_code = f"SUP-{last_code + 1:04d}"
            else:
                new_code = "SUP-0001"
            self.code = new_code
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class PurchaseInvoice(models.Model):
    number = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    sales_rep = models.ForeignKey('sales.SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.SET_NULL, related_name='purchase_invoice')
    is_posted = models.BooleanField(default=False)
    total_before_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_with_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "فاتورة المشتريات"
        verbose_name_plural = "فاتورة المشتريات"

    def __str__(self):
        return f"{self.number}"

    

    def save(self, *args, **kwargs):
        if not self.number:
            last_invoice = PurchaseInvoice.objects.order_by('-id').first()
            if last_invoice and last_invoice.number:
                try:
                    last_number = int(last_invoice.number.split('-')[-1])
                except ValueError:
                    last_number = 0
            else:
                last_number = 0
            new_number = last_number + 1
            self.number = f"Pur.invo-{new_number:05d}"
        super().save(*args, **kwargs)


    def post_invoice(self):
        from inventory.models import StockTransaction, StockTransactionItem, WarehouseOrder, WarehouseOrderItem
        from django.contrib.contenttypes.models import ContentType
        from accounts.models import JournalEntry, JournalEntryLine

        if self.is_posted:
            raise Exception("الفاتورة مرحّلة مسبقًا.")

        if not self.supplier.account or not self.supplier.purchases_account or not self.supplier.vat_account or not self.warehouse.inventory_account:
            raise Exception("تأكد من إعداد جميع الحسابات المرتبطة.")

        # حذف قيود أو حركات سابقة
        if self.journal_entry:
            self.journal_entry.delete()
        StockTransaction.objects.filter(purchase_invoice=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()

        # حساب الإجماليات
        total_before = sum(i.total_before_tax for i in self.items.all())
        total_tax = sum(i.tax_amount for i in self.items.all())
        total_total = total_before + total_tax

        self.total_before_tax_value = total_before
        self.total_tax_value = total_tax
        self.total_with_tax_value = total_total
        self.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])

        # إنشاء قيد اليومية
        entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"قيد آلي ناتج عن فاتورة مشتريات رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(PurchaseInvoice),
            object_id=self.id
        )

        # قيود اليومية (مدين)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.warehouse.inventory_account,
            debit=total_before,
            credit=0,
            description="إضافة للمخزون من فاتورة مشتريات"
        )
        if total_tax > 0:
            JournalEntryLine.objects.create(
                journal_entry=entry,
                account=self.supplier.vat_account,
                debit=total_tax,
                credit=0,
                description="ضريبة القيمة المضافة على المشتريات"
            )

        # قيود اليومية (دائن)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.supplier.account,
            debit=0,
            credit=total_total,
            description="رصيد مستحق للمورد"
        )

        # أمر مستودع
        order = WarehouseOrder.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            type='in',
            reference=f"فاتورة مشتريات رقم {self.number}",
            notes="إدخال بضاعة من فاتورة مشتريات"
        )

        # حركة مخزون
        stock_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            transaction_type='in',
            related_account=self.supplier.purchases_account,
            purchase_invoice=self,
            notes="إدخال بضاعة من فاتورة مشتريات"
        )

        for item in self.items.all():
            unit = item.product.base_unit or item.product.small_unit
            WarehouseOrderItem.objects.create(order=order, product=item.product, quantity=item.quantity, unit=unit)
            StockTransactionItem.objects.create(transaction=stock_tx, product=item.product, quantity=item.quantity, unit=unit, cost=item.unit_price)

        # إجمالي تكلفة المخزون (من حركة الصنف)
        cost_total = sum(item.total_cost for item in stock_tx.items.all())

        # ✅ إضافة قيد تكلفة المخزون داخل نفس قيد الفاتورة
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.warehouse.inventory_account,
            debit=cost_total,
            credit=0,
            description="زيادة المخزون من حركة المشتريات"
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.supplier.purchases_account,
            debit=0,
            credit=cost_total,
            description="مقابل المخزون (تكلفة المشتريات)"
        )

        order.is_posted = True
        order.save()
        stock_tx.is_posted = True
        stock_tx.save()

        self.journal_entry = entry
        self.is_posted = True
        self.save(update_fields=["journal_entry", "is_posted"])

    def unpost_invoice(self):
        from inventory.models import StockTransaction, WarehouseOrder
        if self.journal_entry:
            self.journal_entry.delete()
        StockTransaction.objects.filter(purchase_invoice=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()
        self.journal_entry = None
        self.is_posted = False
        self.save()


class PurchaseInvoiceItem(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name='items')
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


class PurchaseReturn(models.Model):
    number = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField()
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    sales_rep = models.ForeignKey('sales.SalesRepresentative', on_delete=models.SET_NULL, null=True, blank=True)
    original_invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    journal_entry = models.OneToOneField(JournalEntry, null=True, blank=True, on_delete=models.SET_NULL)
    is_posted = models.BooleanField(default=False)

    total_before_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_with_tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        verbose_name = "فاتورة مردودات مشتريات"
        verbose_name_plural = "فاتورة مردودات المشتريات"

    def save(self, *args, **kwargs):
        if not self.number:
            last = PurchaseReturn.objects.all().order_by('id').last()
            if last and last.number:
                last_number = int(last.number.split('-')[-1])
            else:
                last_number = 0
            self.number = f"Pur.ret-{str(last_number + 1).zfill(5)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.number
    

    def post_return(self):
        from inventory.models import StockTransaction, StockTransactionItem, WarehouseOrder, WarehouseOrderItem
        from django.contrib.contenttypes.models import ContentType
        from accounts.models import JournalEntry, JournalEntryLine

        if self.is_posted:
            raise Exception("تم ترحيل مردود المشتريات مسبقًا.")
        if not self.supplier.account or not self.supplier.purchases_account or not self.supplier.vat_account:
            raise Exception("تأكد من إعداد حسابات المورد.")
        if not self.warehouse.inventory_account:
            raise Exception("تأكد من إعداد حساب المستودع.")

        # حذف أي حركات سابقة
        if self.journal_entry:
            self.journal_entry.delete()

        StockTransaction.objects.filter(purchase_return=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()

        # إنشاء القيد المحاسبي
        journal_entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"قيد آلي ناتج عن مردودات مشتريات رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(PurchaseReturn),
            object_id=self.id
        )

        # قيد المورد (عكس الدين)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.supplier.account,
            debit=self.total_with_tax_value,
            credit=0,
            description="إلغاء رصيد مستحق للمورد"
        )

        # قيد المخزون (عكس المخزون)
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.warehouse.inventory_account,
            debit=0,
            credit=self.total_before_tax_value,
            description="عكس المخزون المرتجع"
        )

        # قيد الضريبة
        if self.total_tax_value > 0:
            JournalEntryLine.objects.create(
                journal_entry=journal_entry,
                account=self.supplier.vat_account,
                debit=0,
                credit=self.total_tax_value,
                description="عكس ضريبة المشتريات"
            )

        # إنشاء أمر المستودع
        order = WarehouseOrder.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            type='out',
            reference=f"مردود مشتريات رقم {self.number}",
            notes="صرف بضاعة مردودة من المشتريات"
        )

        # إنشاء حركة الصنف
        stock_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            transaction_type='out',
            related_account=self.supplier.purchases_account,
            purchase_return=self,
            notes=f"صرف بضاعة مردودة من المشتريات"
        )

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

        # احتساب تكلفة المخزون الفعلية للمردود
        cost_total = sum(item.total_cost for item in stock_tx.items.all())

        # إنشاء قيد تكلفة المخزون بنفس منطق المشتريات
        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.supplier.purchases_account,
            debit=cost_total,
            credit=0,
            description="عكس تكلفة المشتريات"
        )

        JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=self.warehouse.inventory_account,
            debit=0,
            credit=cost_total,
            description="تخفيض المخزون نتيجة المرتجع"
        )

        order.is_posted = True
        order.save()
        stock_tx.is_posted = True
        stock_tx.save()

        self.journal_entry = journal_entry
        self.is_posted = True
        self.save(update_fields=["journal_entry", "is_posted"])


    def unpost_return(self):
        from inventory.models import StockTransaction
        JournalEntry.objects.filter(content_type=ContentType.objects.get_for_model(PurchaseReturn), object_id=self.id).delete()
        StockTransaction.objects.filter(purchase_return=self).delete()
        WarehouseOrder.objects.filter(reference__icontains=self.number).delete()
        self.journal_entry = None
        self.is_posted = False
        self.save(update_fields=["journal_entry", "is_posted"])

class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, related_name="details", on_delete=models.CASCADE)
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
###########################################################################################################
# models.py (داخل purchases)from django.db import models
from django.db import models
from accounts.models import Account, JournalEntry, JournalEntryLine
from django.contrib.contenttypes.models import ContentType
from purchases.models import PurchaseInvoice, Supplier
from treasury.models import TreasuryBox

class SupplierPayment(models.Model):
    number = models.CharField(max_length=20, unique=True, verbose_name='رقم السداد')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='المورد')
    date = models.DateField(verbose_name='تاريخ السداد')
    treasury_box = models.ForeignKey(
        TreasuryBox,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='الصندوق / البنك'
    )
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, verbose_name='رقم الفاتورة')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='المبلغ')
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "دفعة مورد"
        verbose_name_plural = "دفعات الموردين"


    def __str__(self):
        return f"سداد {self.supplier} - {self.amount}"

    def save(self, *args, **kwargs):
        creating = self.pk is None

        if not self.number:
            last_payment = SupplierPayment.objects.order_by('-id').first()
            if last_payment and last_payment.number:
                try:
                    last_number = int(last_payment.number.replace('spay-', ''))
                except:
                    last_number = 0
                self.number = f"spay-{str(last_number + 1).zfill(5)}"
            else:
                self.number = "spay-00001"

        super().save(*args, **kwargs)

        if self.journal_entry:
            self.journal_entry.delete()
            self.journal_entry = None
            super().save(update_fields=['journal_entry'])

        if not self.treasury_box:
            raise ValueError("يجب اختيار صندوق أو بنك.")
        if not self.treasury_box.account:
            raise ValueError("يجب تحديد الحساب المرتبط بالصندوق/البنك.")

        debit_account = self.supplier.account
        credit_account = self.treasury_box.account
        box_type_label = "نقدًا" if self.treasury_box.box_type == 'cash' else "تحويل بنكي"

        entry = JournalEntry.objects.create(
            date=self.date,
            notes=f"سند صرف للمورد {self.supplier.name} رقم {self.number}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(SupplierPayment),
            object_id=self.id
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=debit_account,
            debit=self.amount,
            credit=0,
            description=f"سداد فاتورة للمورد رقم {self.number} | {self.supplier.name}"
        )
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=credit_account,
            debit=0,
            credit=self.amount,
            description=f"صرف من الصندوق {box_type_label} رقم {self.number} | {self.supplier.name}"
        )

        self.journal_entry = entry
        super().save(update_fields=['journal_entry'])

    def delete(self, *args, **kwargs):
        if self.journal_entry:
            self.journal_entry.delete()
        super().delete(*args, **kwargs)

###########################################################################################################







