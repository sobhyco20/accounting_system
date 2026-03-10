from django import forms
from .models import PurchaseInvoiceItem, PurchaseReturnItem,SupplierPayment,PurchaseInvoice


class PurchaseInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseInvoiceItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['total_before_tax', 'tax_amount', 'total_with_tax']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'readonly': 'readonly',
                    'style': 'background-color: #f0f0f0;',  # تحسين العرض
                })



class PurchaseReturnItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseReturnItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['total_before_tax', 'tax_amount', 'total_with_tax']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'readonly': 'readonly',
                    'style': 'background-color: #f0f0f0;',  # تحسين العرض
                })
####################################################################################################
from django import forms
from .models import SupplierPayment, PurchaseInvoice, TreasuryBox
from django.db.models import Sum

class SupplierPaymentForm(forms.ModelForm):
    class Meta:
        model = SupplierPayment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['treasury_box'].widget.attrs.update({'id': 'id_treasury_box'})
        self.fields['treasury_box'].queryset = self.fields['treasury_box'].queryset.select_related('account')

        supplier_id = self.data.get('supplier') or getattr(self.instance, 'supplier_id', None)
        if supplier_id:
            try:
                supplier_id = int(supplier_id)
                self.fields['invoice'].queryset = PurchaseInvoice.objects.filter(supplier_id=supplier_id)
            except (ValueError, TypeError):
                self.fields['invoice'].queryset = PurchaseInvoice.objects.none()
        else:
            self.fields['invoice'].queryset = PurchaseInvoice.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')

        if not invoice:
            raise forms.ValidationError("يجب اختيار الفاتورة قبل السداد.")

        total_invoice = invoice.total_with_tax_value
        total_paid = invoice.supplierpayment_set.exclude(pk=self.instance.pk).aggregate(
            total=Sum('amount'))['total'] or 0
        remaining = total_invoice - total_paid

        if amount is None:
            amount = 0

        if amount > remaining:
            raise forms.ValidationError(f"المبلغ المسدد أكبر من المتبقي في الفاتورة ({remaining}).")

        return cleaned_data