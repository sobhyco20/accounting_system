from django.contrib import admin
from .models import TreasuryBox, TreasuryVoucher
from django.http import HttpResponseRedirect



@admin.register(TreasuryBox)
class TreasuryBoxAdmin(admin.ModelAdmin):
    list_display = ['name', 'box_type', 'account', 'opening_balance']
    fields = ['name', 'box_type', 'account', 'opening_balance']

    
@admin.register(TreasuryVoucher)
class TreasuryVoucherAdmin(admin.ModelAdmin):
    list_display = ['code', 'voucher_type', 'amount', 'date', 'responsible']
    search_fields = ['code', 'description']
    autocomplete_fields = ['responsible']
    readonly_fields = ['code', 'journal_entry']



from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from .models import TreasuryReportsFakeModel

@admin.register(TreasuryReportsFakeModel)
class TreasuryReportsAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect(reverse('treasury:reports_home'))