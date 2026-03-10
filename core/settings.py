from pathlib import Path
import os

# =========================================================
# BASE DIR
# =========================================================
BASE_DIR = Path(__file__).resolve().parent.parent


# =========================================================
# ENV HELPER
# =========================================================
def env(name, default=None):
    return os.environ.get(name, default)


# =========================================================
# SECURITY
# =========================================================
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")

DEBUG = env("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = [
    h.strip()
    for h in env("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")
    if h.strip()
]


# =========================================================
# APPLICATIONS
# =========================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django_dynamic_admin_forms',

    # Your Apps
    'accounts',
    'treasury',
    'inventory',
    'manufacturing',
    'sales',
    'core',
    'purchases',
    'dashboard',
    'hr',
    'budget',
    'portal',
]


# =========================================================
# MIDDLEWARE
# =========================================================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# =========================================================
# URLS & WSGI
# =========================================================
ROOT_URLCONF = 'core.urls'
WSGI_APPLICATION = 'core.wsgi.application'


# =========================================================
# TEMPLATES
# =========================================================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'core' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# =========================================================
# DATABASE
# =========================================================
DATABASES = {
    "default": {
        "ENGINE": env("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": env("DB_NAME", str(BASE_DIR / "db.sqlite3")),
        "USER": env("DB_USER", ""),
        "PASSWORD": env("DB_PASSWORD", ""),
        "HOST": env("DB_HOST", ""),
        "PORT": env("DB_PORT", ""),
        "OPTIONS": {
            "timeout": int(env("SQLITE_TIMEOUT", "20")),
        } if env("DB_ENGINE", "django.db.backends.sqlite3") == "django.db.backends.sqlite3" else {},
    }
}


# =========================================================
# PASSWORD VALIDATION
# =========================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# =========================================================
# INTERNATIONALIZATION
# =========================================================
LANGUAGE_CODE = 'ar'
TIME_ZONE = 'Asia/Riyadh'
USE_I18N = True
USE_TZ = True


# =========================================================
# STATIC & MEDIA
# =========================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# =========================================================
# AUTH REDIRECTS
# =========================================================
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "app_home"
LOGOUT_REDIRECT_URL = "login"


# =========================================================
# SECURITY SETTINGS (Production Ready)
# =========================================================
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # HSTS (فعّلها بعد تأكد SSL يعمل)
    SECURE_HSTS_SECONDS = int(env("SECURE_HSTS_SECONDS", "0"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # CSRF Trusted Domains
    _csrf = env("CSRF_TRUSTED_ORIGINS", "")
    CSRF_TRUSTED_ORIGINS = [
        x.strip() for x in _csrf.split(",") if x.strip()
    ]

    X_FRAME_OPTIONS = "SAMEORIGIN"
else:
    # أثناء التطوير
    X_FRAME_OPTIONS = "ALLOWALL"


# =========================================================
# EXTRA
# =========================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20000