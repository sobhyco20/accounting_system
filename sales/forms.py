from django import forms
from .models import SalesInvoiceItem, SalesReturnItem ,CustomerPayment
from django.db.models import Sum


class SalesInvoiceItemForm(forms.ModelForm):
    class Meta:
        model = SalesInvoiceItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['total_before_tax', 'tax_amount', 'total_with_tax']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'readonly': 'readonly',
                    'style': 'background-color: #f0f0f0;',  # تحسين العرض
                })


class SalesReturnItemForm(forms.ModelForm):
    class Meta:
        model = SalesReturnItem
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['total_before_tax', 'tax_amount', 'total_with_tax']:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'readonly': 'readonly',
                    'style': 'background-color: #f0f0f0;',  # تحسين العرض
                })

from django import forms
from .models import CustomerPayment, SalesInvoice, TreasuryBox
from django.db.models import Sum

class CustomerPaymentForm(forms.ModelForm):
    class Meta:
        model = CustomerPayment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fields['treasury_box'].widget.attrs.update({'id': 'id_treasury_box'})
        self.fields['treasury_box'].queryset = self.fields['treasury_box'].queryset.select_related('account')
        # تحميل فواتير العميل فقط
        customer_id = self.data.get('customer') or getattr(self.instance, 'customer_id', None)
        if customer_id:
            try:
                customer_id = int(customer_id)
                self.fields['invoice'].queryset = SalesInvoice.objects.filter(customer_id=customer_id)
            except (ValueError, TypeError):
                self.fields['invoice'].queryset = SalesInvoice.objects.none()
        else:
            self.fields['invoice'].queryset = SalesInvoice.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        invoice = cleaned_data.get('invoice')
        amount = cleaned_data.get('amount')

        if not invoice:
            raise forms.ValidationError("يجب اختيار الفاتورة قبل السداد.")

        total_invoice = invoice.total_with_tax_value
        total_paid = invoice.customerpayment_set.exclude(pk=self.instance.pk).aggregate(
            total=Sum('amount'))['total'] or 0
        remaining = total_invoice - total_paid

        if amount is None:
            amount = 0

        if amount > remaining:
            raise forms.ValidationError(f"المبلغ المسدد أكبر من المتبقي في الفاتورة ({remaining}).")

        return cleaned_data
