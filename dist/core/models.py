# core/models.py أو settings/models.py
from django.db import models

class CompanyProfile(models.Model):
    name = models.CharField("اسم الشركة", max_length=255)
    tax_number = models.CharField(max_length=50, verbose_name="الرقم الضريبي", blank=True, null=True)
    logo = models.ImageField("شعار الشركة", upload_to='company_logo/', blank=True, null=True)
    address = models.TextField("العنوان", blank=True)
    phone = models.CharField("الهاتف", max_length=50, blank=True)
    email = models.EmailField("البريد الإلكتروني", blank=True)
    website = models.URLField("الموقع الإلكتروني", blank=True)
    footer_note = models.TextField("ملاحظة في التذييل", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "بيانات الشركة"
        verbose_name_plural = "بيانات الشركة"
