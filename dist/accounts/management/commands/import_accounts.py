import pandas as pd
from django.core.management.base import BaseCommand
from accounts.models import Account, AccountGroup, SubMapping, AccountDirection, FinancialStatementType

class Command(BaseCommand):
    help = "استيراد الحسابات من ملف accounts.xlsx واستكمال الحسابات الغير موجودة فقط."

    def handle(self, *args, **options):
        file_path = "accounts.xlsx"
        df = pd.read_excel(file_path)

        group_cache = {}
        sub_mapping_cache = {}
        direction_cache = {}
        statement_type_cache = {}
        account_cache = {a.code: a for a in Account.objects.all()}

        for _, row in df.iterrows():
            code = str(row["كود الحساب"]).strip()
            if code in account_cache:
                continue  # الحساب موجود مسبقًا، نتجاوزه

            name = str(row["اسم الحساب"]).strip()
            level = int(row["مستوى الحساب"])

            parent_code = str(row["الحساب الأب"]).strip() if pd.notna(row["الحساب الأب"]) else None
            group_name = str(row["المجموعة"]).strip() if pd.notna(row["المجموعة"]) else None
            sub_mapping_name = str(row["SubMapping"]).strip() if pd.notna(row["SubMapping"]) else None
            direction_name = str(row["التصنيف الداخلي"]).strip() if pd.notna(row["التصنيف الداخلي"]) else None
            statement_type_name = str(row["نوع الحساب (القائمة المالية)"]).strip() if pd.notna(row["نوع الحساب (القائمة المالية)"]) else None

            parent = account_cache.get(parent_code) if parent_code else None

            if group_name:
                group = group_cache.get(group_name)
                if not group:
                    group, _ = AccountGroup.objects.get_or_create(name=group_name)
                    group_cache[group_name] = group
            else:
                group = None

            if sub_mapping_name:
                sub_mapping = sub_mapping_cache.get(sub_mapping_name)
                if not sub_mapping:
                    sub_mapping, _ = SubMapping.objects.get_or_create(name=sub_mapping_name)
                    sub_mapping_cache[sub_mapping_name] = sub_mapping
            else:
                sub_mapping = None

            if direction_name:
                direction = direction_cache.get(direction_name)
                if not direction:
                    direction, _ = AccountDirection.objects.get_or_create(name=direction_name)
                    direction_cache[direction_name] = direction
            else:
                direction = None

            if statement_type_name:
                statement_type = statement_type_cache.get(statement_type_name)
                if not statement_type:
                    statement_type, _ = FinancialStatementType.objects.get_or_create(name=statement_type_name)
                    statement_type_cache[statement_type_name] = statement_type
            else:
                statement_type = None

            account = Account.objects.create(
                code=code,
                name=name,
                level=level,
                parent=parent,
                group=group,
                sub_mapping=sub_mapping,
                direction=direction,
                statement_type=statement_type
            )
            account_cache[code] = account  # نحدث الكاش

        self.stdout.write(self.style.SUCCESS("✅ تم استيراد الحسابات غير الموجودة بنجاح."))
