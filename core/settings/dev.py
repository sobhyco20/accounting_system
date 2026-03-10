from .base import *

DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# لو أنت تستخدم iframe محليًا للتقارير
X_FRAME_OPTIONS = "ALLOWALL"

# اختياري: تقليل تهيئة الكوكيز في التطوير
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False