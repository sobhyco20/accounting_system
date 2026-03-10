from django import forms
from .models import BillOfMaterialsComponent

from .models import BillOfMaterials, Product

class BillOfMaterialsComponentForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterialsComponent
        fields = '__all__'

    class Media:
        js = ('js/bom_component.js',)

class BillOfMaterialsForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterials
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(product_type='finished')

###################################################################################################

class BOMComponentForm(forms.ModelForm):
    class Meta:
        model = BillOfMaterialsComponent
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['component'].queryset = Product.objects.filter(product_type__in=['raw', 'semi'])
