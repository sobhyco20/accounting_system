# core/utils.py
from .models import CompanyProfile

def get_company():
    return CompanyProfile.objects.first()  # أو استخدم cache.get لاحقًا
