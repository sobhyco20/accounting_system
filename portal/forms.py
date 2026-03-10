from django import forms
from django.forms import inlineformset_factory
from sales.models import SalesInvoice, SalesInvoiceItem

class SalesInvoiceForm(forms.ModelForm):
    class Meta:
        model = SalesInvoice
        fields = ["date", "customer"]  # عدّل لو عندك حقول إضافية مثل sales_rep

SalesInvoiceItemFormSet = inlineformset_factory(
    SalesInvoice,
    SalesInvoiceItem,
    fields=["product", "quantity", "unit_price"],  # عدّل حسب حقولك الفعلية
    extra=3,
    can_delete=True
)


from django import forms
from django.forms import inlineformset_factory
from sales.models import SalesReturn, SalesReturnItem

class SalesReturnForm(forms.ModelForm):
    class Meta:
        model = SalesReturn
        fields = "__all__"  # أو حدّد حقول الهيدر مثل invoice تماماً

class SalesReturnItemForm(forms.ModelForm):
    class Meta:
        model = SalesReturnItem
        fields = ["product", "quantity", "unit_price", "tax_rate",
                  "total_before_tax", "tax_amount", "total_with_tax"]

SalesReturnItemFormSet = inlineformset_factory(
    SalesReturn,
    SalesReturnItem,
    form=SalesReturnItemForm,
    extra=1,
    can_delete=True
)