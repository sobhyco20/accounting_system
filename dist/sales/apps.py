from django.apps import AppConfig

class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'sales'
    verbose_name = "3️⃣ العملاء و المبيعات"

    def ready(self):
        import sales.signals  # ← هذا السطر ضروري لتفعيل الإشارات

