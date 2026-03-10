from django.db import models
from inventory.models import Product, Warehouse
from django.utils import timezone 
from accounts.models import Account

# models.py

from django.db import models
from accounts.models import Account
from inventory.models import StockTransaction, StockTransactionItem
from decimal import Decimal
from accounts.models import Account ,JournalEntry,JournalEntryLine
from django.contrib.contenttypes.models import ContentType
##################################################################################################################
class ProductBOMExpense(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='bom_expenses')
    name = models.CharField(max_length=255)
    cost = models.DecimalField(max_digits=10, decimal_places=2)
##################################################################################################################

class ProductionOrderComponent(models.Model):
    order = models.ForeignKey('ProductionOrder', on_delete=models.CASCADE, related_name='components')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit = models.CharField(max_length=50, null=True, blank=True)

    @property
    def total_cost(self):
        quantity = self.quantity or 0
        unit_cost = self.unit_cost or 0
        return quantity * unit_cost

##################################################################################################################
class ProductBOMItem(models.Model):
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='bom_products')
    component = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='component_bom_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20)
    component_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f'{self.product.name} - {self.component.name}'

##################################################################################################################
# في DefaultComponent

class DefaultComponent(models.Model):
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE, related_name='default_bom_components')
    component = models.ForeignKey('inventory.Component', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('product', 'component')

    def __str__(self):
        return f"{self.product.name} - {self.component.name}"


################################################################################################################


class ProductionExpense(models.Model):
    name = models.CharField(max_length=255, verbose_name="اسم المصروف")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, verbose_name="الحساب المالي")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    class Meta:
        verbose_name = "مصروف إنتاج"
        verbose_name_plural = "مصروفات الإنتاج"

    def __str__(self):
        return self.name

##################################مكونات المنتجات####################################################################################

class BillOfMaterials(models.Model):
    product = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    quantity_produced = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    total_component_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_expense_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0)

    def total_component_cost_calc(self):
        return sum(item.total_cost() for item in self.components.all())

    def total_expense_cost_calc(self):
        return sum(item.total for item in self.expenses.all())

    def total_cost_calc(self):
        return self.total_component_cost + self.total_expense_cost

    def unit_cost_calc(self):
        if self.quantity_produced > 0:
            return self.total_cost / self.quantity_produced
        return 0

    def update_totals(self):
        if not self.pk:
            return  # لا يمكن تحديث العلاقات قبل الحفظ الأولي

        self.total_component_cost = self.total_component_cost_calc()
        self.total_expense_cost = self.total_expense_cost_calc()
        self.total_cost = self.total_component_cost + self.total_expense_cost
        self.unit_cost = self.unit_cost_calc()

    def save(self, *args, **kwargs):
        self.update_totals()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"BOM for {self.product}"


class BillOfMaterialsComponent(models.Model):
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name='components')
    component = models.ForeignKey('inventory.Product', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def total_cost(self):
        if self.quantity and self.unit_cost:
            return self.quantity * self.unit_cost
        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.bom:
            self.bom.update_totals()
            self.bom.save()

    def delete(self, *args, **kwargs):
        bom = self.bom
        super().delete(*args, **kwargs)
        if bom:
            bom.update_totals()
            bom.save()

    def __str__(self):
        return f"{self.component} - {self.quantity}"


class AppliedCostToBOM(models.Model):
    bom = models.ForeignKey(BillOfMaterials, on_delete=models.CASCADE, related_name='expenses')
    expense = models.ForeignKey(ProductionExpense, on_delete=models.PROTECT, verbose_name="المصروف")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    @property
    def total(self):
        if self.quantity and self.value:
            return self.quantity * self.value
        return 0

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.bom:
            self.bom.update_totals()
            self.bom.save()

    def delete(self, *args, **kwargs):
        bom = self.bom
        super().delete(*args, **kwargs)
        if bom:
            bom.update_totals()
            bom.save()

    def __str__(self):
        return f"{self.expense.name} - {self.total:.2f}"


####################################اوامر الانتـــــــــــــــــــاج###################################################################################

from decimal import Decimal
from django.db import models
from django.utils import timezone
from inventory.models import Product, Warehouse, StockTransaction, StockTransactionItem
from accounts.models import JournalEntry, JournalEntryLine



class ProductionOrder(models.Model):
    STATUS_CHOICES = [
        ('draft', 'مسودة'),
        ('in_progress', 'قيد التنفيذ'),
        ('done', 'تم الانتهاء'),
        ('cancelled', 'ملغي'),
    ]

    code = models.CharField(max_length=20, unique=True, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, limit_choices_to={'product_type': 'finished'})
    quantity = models.DecimalField(max_digits=10, decimal_places=2)

    raw_material_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='raw_material_orders', limit_choices_to={'warehouse_type': 'raw'}, null=True, blank=True)
    wip_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='wip_orders', limit_choices_to={'warehouse_type': 'wip'}, null=True, blank=True)
    finished_goods_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='finished_orders', limit_choices_to={'warehouse_type': 'finished'}, null=True, blank=True)
    scrap_warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, related_name='scrap_orders', limit_choices_to={'warehouse_type': 'scrap'}, null=True, blank=True)

    finished_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    scrap_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=250, blank=True, null=True)
    is_posted = models.BooleanField(default=False)
    date = models.DateField(default=timezone.now)
    is_materials_issued = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)

    scrap_transaction = models.OneToOneField(StockTransaction, on_delete=models.SET_NULL, null=True, blank=True, related_name='scrap_production_order')

    def __str__(self):
        return self.code

    def save(self, *args, **kwargs):
        if not self.code:
            last_order = ProductionOrder.objects.order_by('-id').first()
            last_number = int(last_order.code.replace('P-ORDER-', '')) if last_order and last_order.code.startswith('P-ORDER-') else 0
            self.code = f'P-ORDER-{last_number + 1:04d}'
        super().save(*args, **kwargs)

    def load_components_from_bom(self):
        try:
            bom = BillOfMaterials.objects.get(product=self.product)
            self.components.all().delete()
            self.expenses.all().delete()
            for item in bom.components.all():
                ProductionOrderComponent.objects.create(
                    order=self,
                    product=item.component,
                    quantity=item.quantity * self.quantity,
                    unit_cost=item.unit_cost
                )
            for exp in bom.expenses.all():
                ProductionOrderExpense.objects.create(
                    order=self,
                    expense=exp.expense,
                    quantity=exp.quantity * self.quantity,
                    value=exp.value
                )
        except BillOfMaterials.DoesNotExist:
            pass

    @property
    def total_component_cost(self):
        return sum(comp.total_cost for comp in self.components.all())

    @property
    def total_expense_cost(self):
        return sum(exp.total for exp in self.expenses.all())

    @property
    def total_cost(self):
        return self.total_component_cost + self.total_expense_cost

    @property
    def unit_cost(self):
        return self.total_cost / self.quantity if self.quantity else Decimal('0.0')

    def post_order(self):
        if self.is_posted:
            raise Exception("تم ترحيل أمر الإنتاج مسبقًا.")

        # 1. ترحيل الحركات المخزنية
        self.post_production_stock_movements()

        # 2. إنشاء القيد المحاسبي
        journal = JournalEntry.objects.create(
            date=self.date,
            reference=f"قيد إنتاج #{self.code}",
            notes=self.notes,
            production_order=self,
            content_type=ContentType.objects.get_for_model(self),
            object_id=self.id
        )

        for component in self.components.all():
            journal.lines.create(
                account=self.raw_material_warehouse.inventory_account,
                debit=0,
                credit=component.total_cost,
                description=f"سحب مكون: {component.product.name}"
            )

        for expense in self.expenses.all():
            journal.lines.create(
                account=expense.expense_account,
                debit=0,
                credit=expense.total,
                description=f"تحميل مصروف: {expense.expense.name}"
            )

        journal.lines.create(
            account=self.finished_goods_warehouse.inventory_account,
            debit=self.total_cost,
            credit=0,
            description="إضافة المنتج التام"
        )

        # 3. الخردة
        if self.scrap_quantity > 0 and self.scrap_warehouse:
            scrap_product, _ = Product.objects.get_or_create(
                code=f"SCRAP-{self.code}",
                defaults={
                    "name": f"خردة ناتجة من أمر إنتاج {self.code}",
                    "product_type": "SCRAP",
                    "base_unit": self.product.base_unit,
                    "large_unit": self.product.large_unit,
                    "small_unit": self.product.small_unit,
                    "conversion_factor": self.product.conversion_factor,
                    "pricing_method": self.product.pricing_method,
                }
            )

            scrap_txn = StockTransaction.objects.create(
                code=f"SCRAP-{self.code}",
                date=self.date,
                warehouse=self.scrap_warehouse,
                transaction_type='in',
                notes=f"إدخال خردة من أمر الإنتاج {self.code}",
                production_order=self,
                is_posted=True
            )

            StockTransactionItem.objects.create(
                transaction=scrap_txn,
                product=scrap_product,
                quantity=self.scrap_quantity,
                cost=0
            )

            self.scrap_transaction = scrap_txn

        self.is_posted = True
        self.status = 'done'
        self.save()

    def unpost_order(self):
        if not self.is_posted:
            raise Exception("لم يتم ترحيل أمر الإنتاج بعد.")

        from accounts.models import JournalEntry
        from inventory.models import StockTransaction

        # 1. حذف قيد أمر الإنتاج
        JournalEntry.objects.filter(production_order=self).delete()

        # 2. حذف قيد حركة الخردة فقط بعد فك العلاقة
        if self.scrap_transaction:
            scrap_tx = self.scrap_transaction
            self.scrap_transaction = None
            self.save()
            scrap_tx.delete()

        # 3. حذف بقية الحركات (بما فيهم حركة الخام والتام)
        other_transactions = StockTransaction.objects.filter(production_order=self)
        for tx in other_transactions:
            if hasattr(tx, 'journal_entry') and tx.journal_entry:
                tx.journal_entry.delete()
        other_transactions.delete()

        # 4. تحديث الحالة
        self.is_posted = False
        self.status = 'draft'
        self.save()




    def post_production_stock_movements(self):
        if self.stock_transactions.exists():
            return

        if not all([self.raw_material_warehouse, self.finished_goods_warehouse, self.finished_quantity]):
            return

        raw_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.raw_material_warehouse,
            transaction_type='out',
            related_account=self.wip_warehouse.inventory_account if self.wip_warehouse else None,
            notes=f"صرف خامات لأمر الإنتاج #{self.code}",
            production_order=self
        )
        for component in self.components.all():
            StockTransactionItem.objects.create(
                transaction=raw_tx,
                product=component.product,
                quantity=component.quantity,
                cost=component.unit_cost,
            )
        raw_tx.post_transaction()

        finished_tx = StockTransaction.objects.create(
            date=self.date,
            warehouse=self.finished_goods_warehouse,
            transaction_type='in',
            related_account=self.finished_goods_warehouse.inventory_account,
            notes=f"إدخال منتج تام لأمر الإنتاج #{self.code}",
            production_order=self
        )
        StockTransactionItem.objects.create(
            transaction=finished_tx,
            product=self.product,
            quantity=self.finished_quantity,
            cost=self.unit_cost,
        )
        finished_tx.post_transaction()

    def delete(self, *args, **kwargs):
        if self.is_posted:
            self.unpost_order()
        super().delete(*args, **kwargs)

    @property
    def total_estimated_cost(self):
        total_materials = sum([m.total_cost() for m in self.materials.all()])
        total_expenses = sum([e.total for e in self.expenses.all()])
        return total_materials + total_expenses

    @property
    def total_variable_cost(self):
        return sum([
            material.total_cost()
            for material in self.materials.all()
        ])


#######################################################################################################################


#######################################################################################################################
class ProductionOrderExpense(models.Model):
    order = models.ForeignKey('ProductionOrder', on_delete=models.CASCADE, related_name='expenses')
    expense = models.ForeignKey(ProductionExpense, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    value = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self):
        return (self.quantity or 0) * (self.value or 0)

    @property
    def amount(self):  # اختياري فقط إن كنت تستخدمه كثيرًا
        return self.total

    @property
    def expense_account(self):
        return self.expense.account



#######################################################################################################################
class ProductionMaterialMovement(models.Model):
    MOVEMENT_TYPE_CHOICES = [
        ('withdraw', 'سحب مواد خام'),
        ('wip_add', 'إضافة إلى تحت التشغيل'),
        ('produce', 'إنتاج منتج تام'),
        ('waste', 'هالك'),
        ('loss', 'فاقد'),
        ('transfer', 'تحويل'),
    ]

    order = models.ForeignKey(ProductionOrder, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPE_CHOICES)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} - {self.quantity}"


class ProductionOrderMaterial(models.Model):
    order = models.ForeignKey(
        'ProductionOrder',
        on_delete=models.CASCADE,
        related_name='materials'  # هذا المطلوب لتفادي الخطأ
    )
    product = models.ForeignKey('inventory.Product', on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    def total_cost(self):
        return (self.quantity or 0) * (self.unit_cost or 0)

