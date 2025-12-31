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
    
    # Local apps
    'accounts',
    'workers',
    'clients',
    'jobs',
    'admin_panel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
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
            ],
        },
    },
]

WSGI_APPLICATION = 'worker_connect.wsgi.application'


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
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

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
# HTTPS and Security Headers (Enable in production with HTTPS)
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)

# Secure Cookies (Enable in production with HTTPS)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection

CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
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
]

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
CELERY_TIMEZONE = TIME_ZONE
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
if config('REDIS_URL', default=None):
    CACHES['default'] = {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL'),
    }

# Custom Exception Handler for standardized error responses
REST_FRAMEWORK['EXCEPTION_HANDLER'] = 'worker_connect.error_codes.custom_exception_handler'
