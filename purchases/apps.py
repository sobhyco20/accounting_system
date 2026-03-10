from django.apps import AppConfig

class PurchasesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'purchases'
    verbose_name = "2️⃣ الموردين و المشتريات"

    def ready(self):
        import purchases.signals  # إذا كان لديك إشارات signals



