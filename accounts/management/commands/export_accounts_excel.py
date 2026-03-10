from django.core.management.base import BaseCommand
from accounts.models import Account
from openpyxl import Workbook
from django.utils.timezone import now

class Command(BaseCommand):
    help = "تصدير قائمة الحسابات إلى ملف Excel"

    def handle(self, *args, **kwargs):
        wb = Workbook()
        ws = wb.active
        ws.title = "Accounts"

        # العناوين
        ws.append([
            "كود الحساب",
            "اسم الحساب",
            "المستوى",
            "الحساب الأب",
            "نوع الحساب",
            "التصنيف الداخلي",
            "مجموعة التدفقات النقدية",
            "Sub-Mapping",
        ])

        # البيانات
        for acc in Account.objects.all().order_by('code'):
            ws.append([
                acc.code,
                acc.name,
                acc.level,
                acc.parent.name if acc.parent else '',
                acc.get_statement_type_display() if acc.statement_type else '',
                acc.get_direction_display() if acc.direction else '',
                acc.group.name if acc.group else '',
                acc.sub_mapping.name if acc.sub_mapping else '',
            ])

        filename = f"accounts_export_{now().date()}.xlsx"
        wb.save(filename)
        self.stdout.write(self.style.SUCCESS(f"✅ تم حفظ ملف الحسابات: {filename}"))
