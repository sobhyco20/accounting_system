from django.db import models
from decimal import Decimal
from accounts.models import Account ,JournalEntry
from django.shortcuts import redirect, get_object_or_404
from django.contrib import admin, messages
from decimal import Decimal
from django.db.models import Sum, F, Q
from django.contrib.contenttypes.models import ContentType
from accounts.models import JournalEntry, JournalEntryLine


class Component(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
###################################################################################################################################

class Warehouse(models.Model):
    WAREHOUSE_TYPES = (
        ('main', 'رئيسي'),
        ('branch', 'فرعي'),
        ('external', 'خارجي'),
        ('raw', 'مواد خام'),
        ('wip', 'تحت التشغيل'),
        ('finished', 'منتج تام'),
        ('scrap', 'هالك'),
    )

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    warehouse_type = models.CharField(max_length=10, choices=WAREHOUSE_TYPES)

    inventory_account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name='warehouses'
    )

    opening_balance_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='opening_balance_warehouses'
    )


    class Meta:
        verbose_name = "مستودع"
        verbose_name_plural = "المستودعات"


    # ✅ حساب تكلفة الإنتاج
    production_cost_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='warehouse_production_cost',
        verbose_name='حساب تكلفة الإنتاج'
    )

    # ✅ حساب تحميل المصروفات الصناعية
    expense_allocation_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='warehouse_expense_allocation',
        verbose_name='حساب تحميل المصروفات'
    )

    def __str__(self):
        return f"{self.code} - {self.name}"

###########################################################################################################################################

class Unit(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=50)
    is_base = models.BooleanField(default=False)
    parent_unit = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    conversion_factor = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)


    class Meta:
        verbose_name = "وحدة"
        verbose_name_plural = "الوحدات"

    def __str__(self):
        return self.name

########################################################################################################
########################################################################################################

class Product(models.Model):
    PRODUCT_TYPES = (
        ('raw', 'مواد خام'),
        ('semi', 'نصف مصنع'),
        ('finished', 'منتج نهائي'),
        ('SCRAP', 'خردة- سكراب'),
    )

    PRICING_METHODS = (
        ('fifo', 'الوارد أولاً يصرف أولاً'),
        ('average', 'متوسط التكلفة'),
    )

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES)

    base_unit = models.ForeignKey(Unit, on_delete=models.PROTECT, related_name='base_products', null=True, blank=True)
    large_unit = models.ForeignKey(Unit, related_name='large_unit_products', on_delete=models.PROTECT)
    small_unit = models.ForeignKey(Unit, related_name='small_unit_products', on_delete=models.PROTECT)
    conversion_factor = models.DecimalField(max_digits=10, decimal_places=4)

    class Meta:
        verbose_name = "منتج"
        verbose_name_plural = "المنتجات"

    pricing_method = models.CharField(
        max_length=10,
        choices=PRICING_METHODS,
        default='fifo',
        verbose_name='طريقة احتساب التكلفة'
    )

    bom_components = models.ManyToManyField(
        'inventory.Component',
        through='manufacturing.DefaultComponent',
        related_name='used_in_products'
    )

    def __str__(self):
        return self.name
    
    average_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def get_average_cost(self):
        from inventory.models import StockTransactionItem
        movements = StockTransactionItem.objects.filter(product=self).order_by('transaction__date')

        total_qty = Decimal('0.00')
        total_cost = Decimal('0.00')

        for item in movements:
            qty = item.quantity or Decimal('0.00')
            cost = item.cost or Decimal('0.00')
            if item.transaction.transaction_type == 'in':
                total_cost += qty * cost
                total_qty += qty
            elif item.transaction.transaction_type == 'out':
                total_qty -= qty

        return (total_cost / total_qty) if total_qty > 0 else Decimal('0.00')

    def __str__(self):
        return f"{self.code} - {self.name}"




    def get_fifo_cost(product, quantity_needed):
        """
        حساب تكلفة الكمية المطلوبة للمنتج باستخدام طريقة FIFO.
        """
        quantity_needed = abs(quantity_needed)
        remaining_qty = quantity_needed
        total_cost = Decimal('0.00')

        # جلب الحركات الواردة (in) مرتبة حسب التاريخ
        incoming_items = StockTransactionItem.objects.filter(
            product=product,
            transaction__transaction_type='in'
        ).order_by('transaction__date', 'id')

        for item in incoming_items:
            # الكمية المصروفة من هذه الحركة
            total_out = StockTransactionItem.objects.filter(
                product=product,
                transaction__transaction_type='out',
                transaction__date__gte=item.transaction.date,
                cost=item.cost  # نفترض نفس التكلفة
            ).aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

            available_qty = item.quantity - total_out
            if available_qty <= 0:
                continue

            use_qty = min(available_qty, remaining_qty)
            total_cost += use_qty * (item.cost or Decimal('0.00'))
            remaining_qty -= use_qty

            if remaining_qty <= 0:
                break

        if remaining_qty > 0:
            raise Exception(f"⚠️ لا توجد كمية كافية في المخزون للمنتج: {product}")

        return total_cost / quantity_needed  # متوسط تكلفة الوحدة

#################################################################################################
# models.py داخل inventory


# inventory/models.py
from django.core.exceptions import ValidationError

class OpeningStockBalance(models.Model):
    warehouse = models.ForeignKey('Warehouse', on_delete=models.PROTECT)
    date = models.DateField()
    is_posted = models.BooleanField(default=False, verbose_name="تم الترحيل")

    class Meta:
        verbose_name = "رصيد افتتاحي للمخزون"
        verbose_name_plural = "الأرصدة الافتتاحية للمخزون"
        constraints = [
            models.UniqueConstraint(fields=["warehouse", "date"], name="uniq_opening_balance_warehouse_date")
        ]

    def __str__(self):
        return f"رصيد أول المدة - {self.warehouse.name}"

    def post_balance(self):
        if self.is_posted:
            raise Exception("تم ترحيل هذا السجل مسبقًا.")

        from inventory.models import StockTransaction, StockTransactionItem

        tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.warehouse,
            transaction_type='in',
            notes=f"Opening Balance #{self.id}",  # 👈 تمييز فريد
        )

        for item in self.items.all():
            StockTransactionItem.objects.create(
                transaction=tx,
                product=item.product,
                quantity=item.quantity,
                unit=item.unit,
                cost=item.unit_cost
            )

        self.is_posted = True
        self.save(update_fields=["is_posted"])


    def unpost_balance(self):
        if not self.is_posted:
            raise Exception("الرصيد غير مرحل مسبقًا.")

        from inventory.models import StockTransaction

        StockTransaction.objects.filter(
            warehouse=self.warehouse,
            date=self.date,
            notes=f"Opening Balance #{self.id}",  # 👈 نفس التمييز
        ).delete()

        self.is_posted = False
        self.save(update_fields=["is_posted"])



    def clean(self):
        super().clean()
        qs = OpeningStockBalance.objects.filter(warehouse=self.warehouse, date=self.date)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError("يوجد رصيد افتتاحي بالفعل لنفس المستودع ونفس التاريخ.")


class OpeningStockItem(models.Model):
    balance = models.ForeignKey(OpeningStockBalance, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost


################################################################################################


class InventoryReportsDummy(models.Model):
    class Meta:
        managed = False
        verbose_name = "تقرير حركة الأصناف"
        verbose_name_plural = "تقرير حركة الأصناف"


class InventoryBalanceDummy(models.Model):
    class Meta:
        managed = False
        verbose_name = "تقرير أرصدة الأصناف"
        verbose_name_plural = "تقرير أرصدة الأصناف"

    def __str__(self):
        return "تقرير أرصدة الأصناف"
#####################################################################################################
class WarehouseOrder(models.Model):
    ORDER_TYPES = [
        ('out', 'أمر صرف'),
        ('in', 'أمر إضافة'),
    ]

    date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=ORDER_TYPES)
    reference = models.CharField(max_length=100, blank=True, null=True)
    notes = models.CharField(max_length=250, blank=True, null=True)

class WarehouseOrderItem(models.Model):
    order = models.ForeignKey(WarehouseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
####################################################################################################


class StockTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('in', 'إدخال'),
        ('out', 'إخراج'),
        ('adjust', 'تسوية'),
    ]

    date = models.DateField()
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    related_account = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    sales_invoice = models.ForeignKey("sales.SalesInvoice", on_delete=models.SET_NULL, null=True, blank=True)
    sales_return = models.ForeignKey("sales.SalesReturn", on_delete=models.SET_NULL, null=True, blank=True)
    purchase_invoice = models.ForeignKey('purchases.PurchaseInvoice', on_delete=models.SET_NULL, null=True, blank=True)
    purchase_return = models.ForeignKey('purchases.PurchaseReturn', on_delete=models.SET_NULL, null=True, blank=True)
    journal_entry = models.OneToOneField("accounts.JournalEntry", on_delete=models.SET_NULL, null=True, blank=True)
    is_posted = models.BooleanField(default=False, verbose_name="تم الترحيل؟")
    code = models.CharField(max_length=50, blank=True, null=True, unique=True)

    production_order = models.ForeignKey(
        'manufacturing.ProductionOrder',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='stock_transactions',
        verbose_name="أمر الإنتاج المرتبط"
    )

    class Meta:
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"



    @property
    def total_cost(self):
        return sum(item.total_cost for item in self.items.all())


    def post_transaction(self):
        if self.is_posted:
            raise Exception("تم ترحيل هذه الحركة مسبقًا.")

        total = self.total_cost
        if total == 0:
            raise Exception("لا يمكن ترحيل حركة بدون تكلفة.")

        journal = JournalEntry.objects.create(
            date=self.date,
            notes=self.notes or f"قيد تلقائي لحركة {self.get_transaction_type_display()}",
            is_auto=True,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id
        )

        if self.transaction_type == 'out':
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=self.related_account,
                debit=total,
                credit=0,
                description="تكلفة بضاعة مباعة"
            )
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=self.warehouse.inventory_account,
                debit=0,
                credit=total,
                description="تخفيض المخزون"
            )
        elif self.transaction_type == 'in':
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=self.warehouse.inventory_account,
                debit=total,
                credit=0,
                description="زيادة المخزون"
            )
            JournalEntryLine.objects.create(
                journal_entry=journal,
                account=self.related_account,
                debit=0,
                credit=total,
                description="رصيد مقابل المخزون"
            )

        self.journal_entry = journal
        self.is_posted = True
        self.save()
        
    def unpost_transaction(self):
        if not self.is_posted:
            raise Exception("الحركة غير مرحلة.")

        if self.journal_entry:
            self.journal_entry.delete()

        self.journal_entry = None
        self.is_posted = False
        self.save()

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.date} - {self.warehouse}"


class StockTransactionItem(models.Model):
    transaction = models.ForeignKey(StockTransaction, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, editable=False)

    def save(self, *args, **kwargs):
        if self.cost is not None and self.quantity is not None:
            self.total_cost = abs(self.quantity * self.cost)
        else:
            self.total_cost = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} - {self.quantity} × {self.cost}"

#####################################################################################

from decimal import Decimal
from inventory.models import OpeningStockItem, StockTransactionItem

def get_product_balance(product_id, warehouse_id=None):
    """
    إرجاع رصيد المادة في مستودع معين (أو جميع المستودعات إذا لم يُحدد).
    """
    # الرصيد الافتتاحي
    opening_qs = OpeningStockItem.objects.filter(product_id=product_id)
    if warehouse_id:
        opening_qs = opening_qs.filter(balance__warehouse_id=warehouse_id)
    opening_qty = opening_qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

    # الكميات الداخلة
    in_qs = StockTransactionItem.objects.filter(
        product_id=product_id,
        transaction__transaction_type='in'
    )
    if warehouse_id:
        in_qs = in_qs.filter(transaction__warehouse_id=warehouse_id)
    qty_in = in_qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

    # الكميات الخارجة
    out_qs = StockTransactionItem.objects.filter(
        product_id=product_id,
        transaction__transaction_type='out'
    )
    if warehouse_id:
        out_qs = out_qs.filter(transaction__warehouse_id=warehouse_id)
    qty_out = out_qs.aggregate(total=Sum('quantity'))['total'] or Decimal('0.00')

    # الرصيد النهائي = افتتاحي + داخل - خارج
    balance = opening_qty + qty_in - qty_out
    return balance







