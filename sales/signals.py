from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from inventory.models import StockTransaction
from .models import SalesInvoice, SalesReturn

# ============ إشعار عند إنشاء فاتورة مبيعات ============

@receiver(post_save, sender=SalesInvoice)
def create_stock_transaction_for_invoice(sender, instance, created, **kwargs):
    if not created:
        return

    # حذف أي حركات سابقة مرتبطة بهذه الفاتورة (لتفادي التكرار)
    StockTransaction.objects.filter(sales_invoice=instance).delete()

    for item in instance.items.all():
        unit = item.product.base_unit or item.product.small_unit
        StockTransaction.objects.create(
            date=instance.date,
            warehouse=instance.warehouse,
            product=item.product,
            quantity=-item.quantity,  # سالب لأنه صرف بضاعة عند البيع
            unit=unit,
            transaction_type='out',
            related_account=instance.customer.group.cost_account,
            cost=item.unit_price,
            sales_invoice=instance
        )

# ============ حذف حركة الصرف عند حذف الفاتورة ============
# ============ إشعار عند إنشاء مردود مبيعات ============

@receiver(post_save, sender=SalesReturn)
def create_stock_transaction_for_return(sender, instance, created, **kwargs):
    if not created:
        return

    # حذف أي حركات سابقة مرتبطة بهذا المردود
    StockTransaction.objects.filter(sales_return=instance).delete()

    for item in instance.details.all():  # ← تم تعديل السطر هنا
        unit = item.product.base_unit or item.product.small_unit
        StockTransaction.objects.create(
            date=instance.date,
            warehouse=instance.warehouse,
            product=item.product,
            quantity=item.quantity,  # موجب لأنه إدخال عند المرتجع
            unit=unit,
            transaction_type='in',
            related_account=instance.customer.account,
            cost=item.product.cost,
            sales_return=instance
        )

# ============ حذف حركة الإدخال عند حذف المردود ============

@receiver(post_delete, sender=SalesReturn)
def delete_stock_transactions_for_return(sender, instance, **kwargs):
    StockTransaction.objects.filter(sales_return=instance).delete()



# sales/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import SalesReturn, SalesReturnItem
from decimal import Decimal

@receiver([post_save, post_delete], sender=SalesReturnItem)
def update_sales_return_totals(sender, instance, **kwargs):
    sales_return = instance.sales_return
    items = sales_return.details.all()

    total_before = sum(item.total_before_tax for item in items)
    total_tax = sum(item.tax_amount for item in items)
    total_with_tax = total_before + total_tax

    sales_return.total_before_tax_value = total_before
    sales_return.total_tax_value = total_tax
    sales_return.total_with_tax_value = total_with_tax
    sales_return.save(update_fields=["total_before_tax_value", "total_tax_value", "total_with_tax_value"])
