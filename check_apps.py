import sys
import os
from pathlib import Path

# 🔧 أضف مجلد المشروع الرئيسي إلى sys.path (يحتوي على core)
BASE_PROJECT_DIR = Path(__file__).resolve().parent.parent / "accounting_system"
sys.path.insert(0, str(BASE_PROJECT_DIR))

# إعداد البيئة لتشغيل Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)
errors = []

print("🔍 التحقق من التطبيقات المسجلة في INSTALLED_APPS...\n")

for app in settings.INSTALLED_APPS:
    if app.startswith('django.'):
        continue

    app_path = BASE_DIR / app.replace('.', '/')
    init_file = app_path / '__init__.py'

    if not app_path.exists():
        errors.append(f"❌ المجلد غير موجود: {app_path}")
    elif not init_file.exists():
        errors.append(f"⚠️ لا يحتوي على __init__.py: {app_path}")
    else:
        print(f"✅ {app} موجود ويحتوي على __init__.py")

if errors:
    print("\n❗ تم العثور على مشاكل:")
    for err in errors:
        print(err)
else:
    print("\n✅ كل التطبيقات مضبوطة بشكل سليم.")
