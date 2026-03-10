# budget/models.py
from django.db import models
from accounts.models import Account

from django.contrib.auth import get_user_model

class Budget(models.Model):
    name = models.CharField(max_length=255)
    year = models.IntegerField()
    created_by = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.year})"

class BudgetEntry(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.CASCADE)

    jan = models.FloatField(default=0)
    feb = models.FloatField(default=0)
    mar = models.FloatField(default=0)
    apr = models.FloatField(default=0)
    may = models.FloatField(default=0)
    jun = models.FloatField(default=0)
    jul = models.FloatField(default=0)
    aug = models.FloatField(default=0)
    sep = models.FloatField(default=0)
    oct = models.FloatField(default=0)
    nov = models.FloatField(default=0)
    dec = models.FloatField(default=0)

    class Meta:
        unique_together = ['budget', 'account']

    def total(self):
        return sum([
            self.jan, self.feb, self.mar, self.apr, self.may, self.jun,
            self.jul, self.aug, self.sep, self.oct, self.nov, self.dec
        ])




from django.db import models
from django.contrib import admin
from django.http import HttpResponseRedirect

class BudgetReportsFakeModel(models.Model):
    class Meta:
        managed = False  # لا يتم إنشاء جدول فعلي في قاعدة البيانات
        app_label = 'budget'
        verbose_name = "💵 تقارير الموازنة التقديرية"
        verbose_name_plural = "💵 تقارير الموازنة التقديرية"

    def __str__(self):
        return "💵 تقارير الموازنة التقديرية"

#@admin.register(BudgetReportsFakeModel)
class BudgetReportsFakeModelAdmin(admin.ModelAdmin):
    def changelist_view(self, request, extra_context=None):
        return HttpResponseRedirect('/budget/reports/')
