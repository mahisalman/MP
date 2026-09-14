"""
Django settings for config project.

Configured with environment variables, custom User model, MySQL support,
email verification settings, and security best practices.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / ".env")

# Core Security Settings
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-default-change-me-in-production-random-key"
)

DEBUG = os.environ.get("DEBUG", "True").strip().lower() in ("true", "1", "t", "yes")

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]


from decimal import Decimal

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Local Modular Apps
    "accounts.apps.AccountsConfig",
    "wallet.apps.WalletConfig",
    "rewards.apps.RewardsConfig",
    "referrals.apps.ReferralsConfig",
    "withdrawals.apps.WithdrawalsConfig",
    "dashboard.apps.DashboardConfig",
    "audit.apps.AuditConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database Configuration
# Primary: MySQL (8.x / MariaDB) with utf8mb4 encoding
# Optional: SQLite fallback for local developer testing when MySQL service is not yet started
USE_SQLITE_FALLBACK = os.environ.get("USE_SQLITE_FALLBACK", "False").strip().lower() in ("true", "1", "t", "yes")

if USE_SQLITE_FALLBACK:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.mysql"),
            "NAME": os.environ.get("DB_NAME", "django_auth_db"),
            "USER": os.environ.get("DB_USER", "root"),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DB_PORT", "3306"),
            "OPTIONS": {
                "charset": "utf8mb4",
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }


# Custom User Model
AUTH_USER_MODEL = "accounts.User"


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Authentication URLs
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:home"
LOGOUT_REDIRECT_URL = "login"


# Verification Code Configuration
VERIFICATION_CODE_EXPIRY_MINUTES = int(os.environ.get("VERIFICATION_CODE_EXPIRY_MINUTES", 10))
VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS = int(os.environ.get("VERIFICATION_CODE_RESEND_COOLDOWN_SECONDS", 45))
VERIFICATION_CODE_MAX_ATTEMPTS = int(os.environ.get("VERIFICATION_CODE_MAX_ATTEMPTS", 5))


# Email Configuration
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "True").strip().lower() in ("true", "1", "t", "yes")
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").strip().lower() in ("true", "1", "t", "yes")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Django Auth <no-reply@example.com>")


# ==============================================================================
# DEMO & SIMULATION PLATFORM SETTINGS
# ==============================================================================
DEMO_MODE = os.environ.get("DEMO_MODE", "True").strip().lower() in ("true", "1", "t", "yes")
SIMULATION_MODE = os.environ.get("SIMULATION_MODE", "True").strip().lower() in ("true", "1", "t", "yes")
CURRENCY_CODE = "DUSD"

# Position & Plan limits
MIN_POSITION_AMOUNT = Decimal("10.00")
MAX_POSITION_AMOUNT = Decimal("10000.00")
MAX_ACTIVE_POSITIONS = 10

# Referral Configuration (2-Level simulation)
MAX_REFERRAL_LEVELS = 2
REFERRAL_LEVEL_1_RATE = Decimal("0.05")  # 5% Level 1
REFERRAL_LEVEL_2_RATE = Decimal("0.02")  # 2% Level 2


# Production Security Headers (Active when DEBUG=False)
if not DEBUG:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"


# Logging Configuration
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}:{lineno} - {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "accounts": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "wallet": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "rewards": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "referrals": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "withdrawals": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
