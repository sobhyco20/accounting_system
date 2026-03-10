from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PurchaseInvoice


@receiver(post_save, sender=PurchaseInvoice)
def purchase_invoice_saved(sender, instance, **kwargs):
    print(f'PurchaseInvoice {instance.id} saved')
