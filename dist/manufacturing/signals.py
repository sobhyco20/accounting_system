from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import BillOfMaterialsComponent, AppliedCostToBOM

@receiver([post_save, post_delete], sender=BillOfMaterialsComponent)
def update_bom_from_component(sender, instance, **kwargs):
    if instance.bom:
        instance.bom.update_totals()

@receiver([post_save, post_delete], sender=AppliedCostToBOM)
def update_bom_from_expense(sender, instance, **kwargs):
    if instance.bom:
        instance.bom.update_totals()
