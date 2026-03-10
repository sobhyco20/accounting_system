from .base import *

DEBUG = False

# لازم تحدد دومينك هنا أو عبر ENV
# ALLOWED_HOSTS تأتي من DJANGO_ALLOWED_HOSTS

# Security
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True

# HSTS (شغّلها بعد ما تتأكد SSL شغال)
SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Clickjacking
X_FRAME_OPTIONS = "SAMEORIGIN"  # لا تستخدم ALLOWALL في الإنتاج

# CSRF trusted origins (مهم مع https)
_csrf = env("CSRF_TRUSTED_ORIGINS", "")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in _csrf.split(",") if x.strip()]