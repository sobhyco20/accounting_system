from django.db import models

# نموذج وهمي لتقارير المبيعات
class SalesReports(models.Model):
    class Meta:
        managed = False
        verbose_name = "تقارير المبيعات"
        verbose_name_plural = "تقارير المبيعات"

# نموذج وهمي لتقارير المشتريات
class PurchasesReports(models.Model):
    class Meta:
        managed = False
        verbose_name = "تقارير المشتريات"
        verbose_name_plural = "تقارير المشتريات"
