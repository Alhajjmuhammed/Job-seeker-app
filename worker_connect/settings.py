"""
Django settings for worker_connect project.
"""

from pathlib import Path
import os
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# Generate a new key: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY = config('SECRET_KEY', default=None)

if not SECRET_KEY:
    if config('DEBUG', default=False, cast=bool):
        # Only allow fallback in explicit debug mode
        SECRET_KEY = 'dev-only-insecure-key-not-for-production'
        import warnings
        warnings.warn(
            "WARNING: Using insecure development SECRET_KEY. "
            "Set SECRET_KEY in .env for production!",
            RuntimeWarning
        )
    else:
        raise ValueError(
            "SECRET_KEY environment variable is required! "
            "Generate one with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'"
        )

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

# SECURITY: Configure allowed hosts from environment
# In development: ALLOWED_HOSTS=localhost,127.0.0.1
# In production: ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='localhost,127.0.0.1,0.0.0.0',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)


# Application definition

INSTALLED_APPS = [
    # Daphne (optional - only needed for production ASGI server)
    # If not installed, Django's development server will handle WebSockets
]

# Add daphne if installed (for production ASGI server)
try:
    import daphne
    INSTALLED_APPS.insert(0, 'daphne')  # Must be first
except ImportError:
    pass  # Daphne not installed, Django dev server will handle WebSockets

INSTALLED_APPS += [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'crispy_forms',
    'crispy_bootstrap5',
    'widget_tweaks',
    'drf_yasg',  # API documentation
    'channels',  # WebSocket support
    
    # Local apps
    'worker_connect',
    'accounts',
    'workers',
    'clients',
    'jobs',
    'admin_panel',
    'agents',
]

MIDDLEWARE = [
    'worker_connect.https_middleware.DevelopmentHTTPSWarningMiddleware',  # Handle HTTPS in dev (must be first)
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',  # Multi-language support
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'worker_connect.request_tracking.RequestIDMiddleware',  # Request ID tracking
    'worker_connect.middleware.APILoggingMiddleware',  # API request/response logging
    'worker_connect.middleware.SecurityHeadersMiddleware',  # Security headers
]

ROOT_URLCONF = 'worker_connect.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'worker_connect.context_processors.admin_counts',
                'worker_connect.context_processors.script_prefix',
            ],
        },
    },
]

WSGI_APPLICATION = 'worker_connect.wsgi.application'

# ASGI Application for WebSocket support
ASGI_APPLICATION = 'worker_connect.asgi.application'

# Channel Layers for WebSocket communication
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',  # Development
    }
}

# Use Redis for Channel Layers in production
if config('REDIS_URL', default=None):
    CHANNEL_LAYERS['default'] = {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [config('REDIS_URL')],
            # another project shares this redis; never share group names
            'prefix': 'workerconnect',
        },
    }


# Database
# Support for DATABASE_URL environment variable (production)
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=config('DB_CONN_MAX_AGE', default=600, cast=int),
            conn_health_checks=True,
        )
    }
    # Add connection pooling options for PostgreSQL
    if 'postgresql' in DATABASE_URL or 'postgres' in DATABASE_URL:
        DATABASES['default']['OPTIONS'] = {
            'connect_timeout': config('DB_CONNECT_TIMEOUT', default=10, cast=int),
        }
else:
    # Default SQLite for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'en-us'

LANGUAGES = [
    ('en', 'English'),
    ('sw', 'Swahili'),
    ('fr', 'Français'),
    ('it', 'Italiano'),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

# Tanzania time: dates ("today", job-post closing dates, reports) and shown times follow
# local time. Times are still STORED in UTC (USE_TZ=True), so no data changes.
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_ROOT = BASE_DIR / 'media'

# When this app is reverse-proxied under a URL prefix (e.g. a second VPS
# sharing port 80 with another app, path-routed instead of its own port),
# set URL_PREFIX so Django-generated links (admin, {% url %}, static, media)
# include it. Leave unset for a deployment with its own dedicated root.
URL_PREFIX = config('URL_PREFIX', default='')
if URL_PREFIX:
    FORCE_SCRIPT_NAME = URL_PREFIX
    STATIC_URL = URL_PREFIX + '/static/'
    MEDIA_URL = URL_PREFIX + '/media/'
else:
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Login/Logout URLs
LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'

# Email Configuration
# For development: console backend (prints to terminal)
# For production: smtp backend with proper settings
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.console.EmailBackend'
)

# SMTP Settings (for production)
# Handle empty strings from .env by using custom cast functions
def _cast_int_or_default(val, default):
    """Cast to int, returning default if empty or invalid"""
    if not val or val == '':
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def _cast_bool_or_default(val, default):
    """Cast to bool, returning default if empty"""
    if not val or val == '':
        return default
    return val.lower() in ('true', '1', 'yes', 'on')

EMAIL_HOST = config('EMAIL_HOST', default='smtp.gmail.com') or 'smtp.gmail.com'
EMAIL_PORT = _cast_int_or_default(config('EMAIL_PORT', default=''), 587)
EMAIL_USE_TLS = _cast_bool_or_default(config('EMAIL_USE_TLS', default=''), True)
EMAIL_USE_SSL = _cast_bool_or_default(config('EMAIL_USE_SSL', default=''), False)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Default sender email
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@workerconnect.com')
SERVER_EMAIL = config('SERVER_EMAIL', default='errors@workerconnect.com')

# Email subject prefix for admin emails
EMAIL_SUBJECT_PREFIX = '[Worker Connect] '

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Security Settings
# HTTPS and Security Headers (DISABLED in development)
# Force disable SSL redirect in development
SECURE_SSL_REDIRECT = False  # Never redirect to HTTPS in development
SECURE_HSTS_SECONDS = 0  # No HSTS
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Secure Cookies (DISABLED in development)
SESSION_COOKIE_SECURE = False  # Allow cookies over HTTP in development
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

CSRF_COOKIE_SECURE = False  # Allow CSRF cookie over HTTP in development
CSRF_COOKIE_HTTPONLY = True  # Prevent JavaScript access to CSRF cookie
CSRF_COOKIE_SAMESITE = 'Lax'

# Security Headers
SECURE_BROWSER_XSS_FILTER = True  # Enable browser XSS protection
SECURE_CONTENT_TYPE_NOSNIFF = True  # Prevent MIME type sniffing
X_FRAME_OPTIONS = 'DENY'  # Prevent clickjacking

# Content Security Policy (Basic configuration)
# For production, customize based on your needs
if not DEBUG:
    CSP_DEFAULT_SRC = ("'self'",)
    CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
    CSP_STYLE_SRC = ("'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net")
    CSP_IMG_SRC = ("'self'", "data:", "https:")
    CSP_FONT_SRC = ("'self'", "https://cdn.jsdelivr.net")

# Session Security
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Password Reset Timeout (24 hours)
PASSWORD_RESET_TIMEOUT = 86400

# Login Attempt Security
# Note: For production, consider installing django-axes or django-ratelimit
# pip install django-axes
# AXES_FAILURE_LIMIT = 5  # Lock after 5 failed attempts
# AXES_COOLOFF_TIME = 1  # Lock for 1 hour

# File Upload Security
FILE_UPLOAD_PERMISSIONS = 0o644  # Restrict file permissions
ALLOWED_UPLOAD_EXTENSIONS = [
    'pdf', 'doc', 'docx', 'txt',  # Documents
    'jpg', 'jpeg', 'png', 'gif', 'webp',  # Images
]

# Ensure logs directory exists
LOGS_DIR = BASE_DIR / 'logs'
LOGS_DIR.mkdir(exist_ok=True)

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'api': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO' if DEBUG else 'WARNING',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'django.log',
            'formatter': 'verbose',
        },
        'security': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': LOGS_DIR / 'security.log',
            'formatter': 'verbose',
        },
        'api_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'api.log',
            'formatter': 'api',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
        },
        # Money has its own log. When a figure on YAS's statement does
        # not match ours, this is the file that settles it, and mixing it
        # into the general log would mean grepping a week of noise.
        'yas_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_DIR / 'yas.log',
            'formatter': 'verbose',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 10,
            # Opened on the first line written, not at startup. Django
            # configures logging inside django.setup(), so a handler
            # that cannot open its file raises before a single URL is
            # served and the whole site refuses to boot. That is
            # exactly what happened once: a management command run as
            # root left this file owned by root, gunicorn runs as
            # www-data, and every worker died with "Unable to configure
            # handler 'yas_file'". A log must never be able to do that.
            'delay': True,
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'] if not DEBUG else ['console'],
            'level': 'INFO' if DEBUG else 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'security'] if not DEBUG else ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'api': {
            'handlers': ['api_file', 'console'] if DEBUG else ['api_file'],
            'level': 'INFO',
            'propagate': False,
        },
        # INFO, not WARNING, and on purpose. The console handler is
        # WARNING in production, so without this every ordinary payment
        # would go unrecorded and only the failures would show.
        'worker_connect.yas': {
            'handlers': ['yas_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Admin Security
ADMIN_URL = config('ADMIN_URL', default='admin/')  # Change in production for security

# Data Sanitization
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000  # Prevent DOS via too many fields

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Anonymous users: 100 requests per hour
        'user': '1000/hour',  # Authenticated users: 1000 requests per hour
    },
    # nginx sits in front and appends the real client address to
    # X-Forwarded-For. Without this DRF keyed throttles on the whole header,
    # which the client controls, so a fresh fake value per request bypassed
    # the login, registration and password-reset limits.
    'NUM_PROXIES': config('NUM_PROXIES', default=1, cast=int),
}

# CORS Configuration
# Configure via environment variable (comma-separated list)
# Example: CORS_ALLOWED_ORIGINS=http://localhost:8081,http://localhost:19006
_cors_origins = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:8081,http://localhost:19006,http://localhost:3000',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# Allow all origins for development (NOT recommended for production)
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)

# If not allowing all origins, use the configured list
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = _cors_origins

# Allow mobile app origins with regex (for Expo development)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r'^https?://192\.168\.\d{1,3}\.\d{1,3}(:\d+)?$',  # Local network devices
    r'^https?://10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?$',  # Private network
    r'^exp://.*$',  # Expo development
] if DEBUG else []  # with credentials allowed, any LAN page could call the live API

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-request-id',
    'x-api-version',
]

CORS_EXPOSE_HEADERS = [
    'x-request-id',
    'x-ratelimit-limit',
    'x-ratelimit-remaining',
    'x-ratelimit-reset',
    'x-api-version',
    'deprecation',
    'sunset',
]

# CORS preflight cache time (in seconds)
CORS_PREFLIGHT_MAX_AGE = 86400  # 24 hours

# Frontend URL for password reset links, etc.
FRONTEND_URL = config('FRONTEND_URL', default='http://localhost:8081')

# API Configuration
API_VERSION = '1.0'
API_TITLE = 'Worker Connect API'

# Analytics Configuration
ANALYTICS_ENABLED = config('ANALYTICS_ENABLED', default=True, cast=bool)

# Celery Configuration
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'  # schedules are written in UTC (celery.py pins it too); 15:00 UTC = 18:00 EAT

# Phone push alerts through Expo (the app registers ExponentPushToken[...] per phone).
# Switched off while the test suite runs, so tests never contact Expo.
import sys as _sys
EXPO_PUSH_ENABLED = (os.environ.get('EXPO_PUSH_ENABLED', 'true').lower() in ('1', 'true', 'yes')
                     and 'test' not in _sys.argv[1:2])
EXPO_ACCESS_TOKEN = os.environ.get('EXPO_ACCESS_TOKEN', '')  # only if push security is turned on in Expo
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': config(
            'CACHE_BACKEND',
            default='django.core.cache.backends.locmem.LocMemCache'
        ),
        'LOCATION': config('CACHE_LOCATION', default='unique-snowflake'),
        'TIMEOUT': config('CACHE_TIMEOUT', default=300, cast=int),
        'OPTIONS': {
            'MAX_ENTRIES': config('CACHE_MAX_ENTRIES', default=1000, cast=int),
        }
    }
}

# Redis cache for production
#
# This server also hosts another Django project, which runs on Redis db 2 but
# whose settings fall back to db 0 if its own .env is ever lost. A REDIS_URL
# with no database path also means db 0, so the two would silently share one
# keyspace - and cache.clear() is a FLUSHDB, which would wipe the other
# project's data. Pin an explicit database, and prefix our keys, so neither
# project can reach the other's.
_redis_url = config('REDIS_URL', default=None)
if _redis_url:
    from urllib.parse import urlparse, urlunparse

    _parts = urlparse(_redis_url)
    if _parts.path in ('', '/'):
        _redis_url = urlunparse(_parts._replace(path='/1'))

    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': _redis_url,
        'KEY_PREFIX': 'wc',
    }

# Custom Exception Handler for standardized error responses
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'worker_connect.error_codes.custom_exception_handler'

# Clear the cache between tests so DRF throttle counters cannot leak from
# one test into the next - see worker_connect/test_runner.py.
TEST_RUNNER = 'worker_connect.test_runner.CacheIsolatingTestRunner'

# Production Security Settings
if not DEBUG:
    # HTTPS-dependent settings used to be unconditionally True here,
    # ignoring whatever .env said - correct for a server with a real SSL
    # cert (workersearch.co.tz), but it silently forced an HTTP-redirect
    # loop and non-functional (never-sent) secure cookies on any
    # deployment without HTTPS in front of it (e.g. a bare-IP mirror).
    # .env is now authoritative; defaults still assume HTTPS is present,
    # matching prior behavior for anyone who doesn't set these explicitly.
    SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=True, cast=bool)
    # TLS ends at nginx, which sets X-Forwarded-Proto. Without this Django
    # only knew a request was HTTPS because of a gunicorn default - any
    # other server (daphne, a changed proxy) would loop on the redirect.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
    SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=True, cast=bool)
    SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
    CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=True, cast=bool)
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# Origins allowed to submit forms over HTTPS (comma-separated).
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://workersearch.co.tz,https://www.workersearch.co.tz',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()]
)

# Payments are simulated until the YAS gateway is connected. A demo
# reference lets a booking go through, but only an admin verifying the
# client's payment proof marks it paid. Turn this on in test environments
# only, to let demo references count as real payment.
DEMO_PAYMENTS_COUNT_AS_PAID = config('DEMO_PAYMENTS_COUNT_AS_PAID', default=False, cast=bool)

# Web login: failed attempts allowed per client address before a lockout.
LOGIN_FAILURE_LIMIT = config('LOGIN_FAILURE_LIMIT', default=10, cast=int)
LOGIN_LOCKOUT_SECONDS = config('LOGIN_LOCKOUT_SECONDS', default=900, cast=int)

# Public address of the site, used for links in e-mails.
SITE_URL = config('SITE_URL', default='https://workersearch.co.tz').rstrip('/')


# ---------------------------------------------------------------------------
# Mixx by YAS
# ---------------------------------------------------------------------------
# Everything here is off and empty until somebody fills it in on purpose.
# EasyFix has an agreed partnership with Mixx by Yas but no biller
# credentials yet, so there is nothing real to put in these and nothing
# would work if there were.
#
# Two switches, because clients paying in and workers being paid out are
# separate decisions and will be turned on at different times:
YAS_CLIENT_PAYMENTS_ENABLED = config(
    'YAS_CLIENT_PAYMENTS_ENABLED', default=False, cast=bool)
YAS_WORKER_PAYOUTS_ENABLED = config(
    'YAS_WORKER_PAYOUTS_ENABLED', default=False, cast=bool)
# Refunds are their own switch again. The push callback refuses to mark a
# booking paid when the amount YAS deducted does not match what it costs,
# and that leaves money taken with nothing given back - this is the way
# out of it, and it moves real money, so it is off until it is wanted.
YAS_REFUNDS_ENABLED = config('YAS_REFUNDS_ENABLED', default=False, cast=bool)

# The switches gate what we *start* - asking a handset for money, sending
# a worker theirs. They do not gate the two callbacks YAS make to us.
# Money that has already left a client's wallet has to be credited to
# their booking whatever a flag says, and the callbacks are inert anyway
# until one of the three things below can identify YAS.

# --- identifying YAS when they call us ------------------------------------
# A secret of our own in a header, their biller username and password
# over HTTP Basic, or their gateway's address. Any one is enough; with
# none of them every callback is refused.
YAS_CALLBACK_SECRET = config('YAS_CALLBACK_SECRET', default='')
# YAS's gateway address, comma separated. Never ours: putting our own
# office address here does not let us test anything, it opens the
# endpoint to everybody who shares that address. That mistake was made
# once already on the other platform.
YAS_ALLOWED_IPS = config('YAS_ALLOWED_IPS', default='')

# --- how our references come home -----------------------------------------
# YAS prefix our reference with the biller code they issue us. Until
# they do, yas.py finds our own reference inside whatever arrives.
YAS_BILLER_CODE = config('YAS_BILLER_CODE', default='')

# --- money in: the Debit Mandate USSD push --------------------------------
# Whole URLs, not a base address with a path added. YAS give each partner
# its own named routes on a shared gateway; the paths printed in the
# specification belong to other billers, and calling them cost a day on
# the other platform.
YAS_TOKEN_URL = config('YAS_TOKEN_URL', default='')
YAS_PAY_URL = config('YAS_PAY_URL', default='')
YAS_BILLER_MSISDN = config('YAS_BILLER_MSISDN', default='')
YAS_BILLER_USERNAME = config('YAS_BILLER_USERNAME', default='')
YAS_BILLER_PASSWORD = config('YAS_BILLER_PASSWORD', default='')

# The Debit Mandate specification gives the callback success code twice
# with different values - BILLER-18-0000-S in the sample, BILLER-30-0000-S
# in the table of expected codes. The table wins, and these let the first
# real test settle it without a deploy.
YAS_CALLBACK_SUCCESS_CODE = config(
    'YAS_CALLBACK_SUCCESS_CODE', default='BILLER-30-0000-S')
YAS_CALLBACK_FAILURE_CODE = config(
    'YAS_CALLBACK_FAILURE_CODE', default='BILLER-30-3030-E')

# --- money out: A2W, their 'MFI CashIn' -----------------------------------
YAS_PAYOUT_URL = config('YAS_PAYOUT_URL', default='')
# Our TigoPesa disbursement account and its PIN. The specification names
# the PIN as the credential for this call.
YAS_DISBURSEMENT_MSISDN = config('YAS_DISBURSEMENT_MSISDN', default='')
YAS_DISBURSEMENT_PIN = config('YAS_DISBURSEMENT_PIN', default='')
# Shown to the worker so they know who paid them, and the numeric brand
# id YAS issue at integration.
YAS_SENDER_NAME = config('YAS_SENDER_NAME', default='Worker Connect')
YAS_BRAND_ID = config('YAS_BRAND_ID', default='')
# Sent verbatim as the Authorization header on the payout call, if YAS
# ask for one. A setting rather than a guess.
YAS_PAYOUT_AUTH = config('YAS_PAYOUT_AUTH', default='')

# --- money back: Refund Transaction ---------------------------------------
# Another whole URL, and again a named route YAS have yet to issue. The
# path printed in their specification, /API/Reverse/ReverseTransacation,
# belongs to somebody else's biller on the shared gateway.
YAS_REFUND_URL = config('YAS_REFUND_URL', default='')
# The merchant/biller number and its MFS PIN, which the refund call
# carries in its body as ChannelMSISDN and ChannelPIN.
YAS_CHANNEL_MSISDN = config('YAS_CHANNEL_MSISDN', default='')
YAS_CHANNEL_PIN = config('YAS_CHANNEL_PIN', default='')

# --- the amount check -----------------------------------------------------
# A booking is priced in shillings and paid in shillings, so this
# comparison is exact and needs no slack - unlike the other platform,
# which prices in dollars and has to allow for the exchange rate. Raise
# it only if YAS turn out to deduct a fee before the money reaches us.
# It only ever allows LESS than the price; paying more than the price is
# always refused (W2A answers error014, a push is not applied).
YAS_AMOUNT_TOLERANCE = config('YAS_AMOUNT_TOLERANCE', default='0')

# --- who may move money -----------------------------------------------------
# Creating, sending and resolving payouts and refunds needs a superuser or
# the permission workers.send_workerpayout / clients.send_clientrefund -
# not merely is_staff. With this on (the default), the person who approved
# a payout or refund cannot also send it, and a payout cannot be sent to a
# number other than the worker's own when it is off.
YAS_REQUIRE_SECOND_APPROVER = config(
    'YAS_REQUIRE_SECOND_APPROVER', default=True, cast=bool)

# --- push prompts -----------------------------------------------------------
# While a prompt is this recent, a new one for the same booking is refused
# (unless YAS have already told us the last one failed). Long enough for a
# client to find their phone and type a PIN; short enough that a missed
# prompt can be retried.
YAS_PROMPT_WINDOW_SECONDS = config(
    'YAS_PROMPT_WINDOW_SECONDS', default=180, cast=int)

# --- outbound timeouts --------------------------------------------------------
# gunicorn kills a worker after 30s (gunicorn_config.py). A money call that
# outlives it leaves its row in 'sending' with nobody to finish it, so the
# token and the money call together stay below that. yas_client clamps
# these to 25s whatever is set here.
YAS_HTTP_TIMEOUT = config('YAS_HTTP_TIMEOUT', default=20, cast=int)
YAS_TOKEN_TIMEOUT = config('YAS_TOKEN_TIMEOUT', default=8, cast=int)
# A payout or refund still 'sending' after this long was cut off mid-call;
# a superuser may then resolve it by hand, with evidence, like a held one.
# Nothing ever retries it automatically.
YAS_STUCK_SENDING_MINUTES = config(
    'YAS_STUCK_SENDING_MINUTES', default=10, cast=int)
