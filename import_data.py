import os
import django

# تحديد ملف الإعدادات
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# تهيئة Django
django.setup()



import csv
from accounts.models import Account
from sales.models import Customer
from purchases.models import Supplier
from inventory.models import Warehouse

# 1- استيراد شجرة الحسابات
with open('C:/Users/SOBHY/Desktop/accounting_system2/accounts.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Account.objects.update_or_create(
            code=row['code'],
            defaults={
                'name': row['name'],
                'parent_id': row['parent_id'] or None,
                'level': row['level'],
                'account_type': row['account_type'],
            }
        )
print('✅ تم استيراد شجرة الحسابات')

# 2- استيراد العملاء
with open('C:/Users/SOBHY/Desktop/accounting_system2/customers.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Customer.objects.update_or_create(
            name=row['name'],
            defaults={
                'phone': row['phone'],
                'email': row['email'],
                'address': row['address'],
            }
        )
print('✅ تم استيراد العملاء')

# 3- استيراد الموردين
with open('C:/Users/SOBHY/Desktop/accounting_system2/suppliers.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Supplier.objects.update_or_create(
            name=row['name'],
            defaults={
                'phone': row['phone'],
                'email': row['email'],
                'address': row['address'],
            }
        )
print('✅ تم استيراد الموردين')

# 4- استيراد المستودعات
with open('C:/Users/SOBHY/Desktop/accounting_system2/warehouses.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        Warehouse.objects.update_or_create(
            code=row['code'],
            defaults={'name': row['name']}
        )
print('✅ تم استيراد المستودعات')
