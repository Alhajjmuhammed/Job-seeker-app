"""
Django settings for worker_connect project.
"""

from pathlib import Path
import os
from decouple import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# SECURITY WARNING: keep the secret key used in production secret!
# CRITICAL: Remove the default in production! Must be set in .env file
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-CHANGE-THIS')

if SECRET_KEY == 'django-insecure-dev-key-CHANGE-THIS':
    import warnings
    warnings.warn(
        "WARNING: You are using the default SECRET_KEY. "
        "This is insecure! Set a proper SECRET_KEY in your .env file.",
        RuntimeWarning
    )

# SECURITY WARNING: don't run with debug turned on in production!
# CRITICAL: Must be False in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = ['*']  # Allow all hosts for development


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

# Email configuration (for production)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

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
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://192.168.100.111:8081",
    "exp://192.168.100.111:8081",
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
]
