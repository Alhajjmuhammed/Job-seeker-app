# 🔒 Security Configuration Guide

## Critical Security Setup

### 1. Environment Variables (.env file)

**NEVER commit your `.env` file to git!** It's already in `.gitignore`.

Create your `.env` file from the example:

```bash
cp .env.example .env
```

### 2. Generate a Strong SECRET_KEY

**CRITICAL:** Generate a new SECRET_KEY for production:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Copy the output and update your `.env` file:

```env
SECRET_KEY=your-generated-secret-key-here
```

### 3. Production Environment Setup

Update your `.env` file for production:

```env
# CRITICAL: Set to False in production
DEBUG=False

# Your production domain
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Enable HTTPS security
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### 4. Database Security

**DO NOT use SQLite in production!** Migrate to PostgreSQL:

```env
# Add to .env
DATABASE_URL=postgresql://user:password@localhost:5432/workerconnect
```

Update database settings to use PostgreSQL (see `settings_production.py`).

### 5. Change Default Admin URL

For security through obscurity, change the admin URL:

```env
# Add to .env
ADMIN_URL=your-secret-admin-path-12345/
```

Then update `worker_connect/urls.py`:

```python
from django.conf import settings
admin_url = getattr(settings, 'ADMIN_URL', 'admin/')
urlpatterns = [
    path(admin_url, admin.site.urls),
    # ... rest of urls
]
```

## Security Checklist

### Before Going Live

- [ ] Generate new SECRET_KEY and add to .env
- [ ] Set DEBUG=False in production .env
- [ ] Configure ALLOWED_HOSTS with your domain
- [ ] Enable HTTPS and set secure cookie flags
- [ ] Migrate from SQLite to PostgreSQL
- [ ] Set up proper email configuration
- [ ] Configure static/media file storage (S3/CDN)
- [ ] Create logs directory: `mkdir -p logs`
- [ ] Set up Redis for caching (optional but recommended)
- [ ] Change default admin URL
- [ ] Configure firewall rules
- [ ] Set up SSL certificates (Let's Encrypt)
- [ ] Configure backup strategy
- [ ] Set up monitoring (Sentry, New Relic, etc.)
- [ ] Run security audit: `python manage.py check --deploy`
- [ ] Review and restrict file upload types
- [ ] Test login rate limiting

### Regular Maintenance

- [ ] Update dependencies regularly: `pip list --outdated`
- [ ] Review security logs: `tail -f logs/security.log`
- [ ] Monitor failed login attempts
- [ ] Review user permissions periodically
- [ ] Backup database daily
- [ ] Rotate SECRET_KEY periodically (requires user re-login)

## Password Security

Current configuration enforces:
- Minimum length validation
- Similarity to user attributes check
- Common password prevention
- Numeric-only password prevention

## File Upload Security

Allowed file types are restricted in settings:
- Documents: PDF, DOC, DOCX, TXT
- Images: JPG, JPEG, PNG, GIF, WEBP

Maximum file size: 10MB

**Recommendation:** Add virus scanning for uploaded files in production.

## Rate Limiting (Recommended)

Install django-axes for brute force protection:

```bash
pip install django-axes
```

Add to `INSTALLED_APPS`:
```python
INSTALLED_APPS += ['axes']
```

Configure:
```python
AXES_FAILURE_LIMIT = 5  # Lock after 5 failed attempts
AXES_COOLOFF_TIME = 1   # Lock for 1 hour
AXES_LOCKOUT_TEMPLATE = 'account_locked.html'
```

## HTTPS Configuration

### Using Nginx (Recommended)

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /path/to/staticfiles/;
    }
    
    location /media/ {
        alias /path/to/media/;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

## Security Testing

### Run Django's Security Check

```bash
python manage.py check --deploy
```

This will warn you about:
- Debug mode in production
- Insecure SECRET_KEY
- Missing security headers
- Insecure cookies
- And more...

### Scan for Vulnerabilities

```bash
# Install safety
pip install safety

# Check for known vulnerabilities
safety check
```

## Monitoring & Alerts

### Set Up Sentry (Recommended)

```bash
pip install sentry-sdk
```

Add to settings:
```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=False,
)
```

## Incident Response

If you suspect a security breach:

1. **Immediate Actions:**
   - Take the site offline if necessary
   - Change SECRET_KEY (forces all users to re-login)
   - Reset all admin passwords
   - Check logs for suspicious activity: `logs/security.log`

2. **Investigation:**
   - Review access logs
   - Check database for unauthorized changes
   - Verify file integrity
   - Look for uploaded malicious files

3. **Recovery:**
   - Restore from clean backup if needed
   - Patch the vulnerability
   - Update all dependencies
   - Notify affected users if data was compromised

## Security Contacts

- Report vulnerabilities to: security@yourdomain.com
- Emergency contact: [Your phone number]

## Additional Resources

- Django Security Docs: https://docs.djangoproject.com/en/4.2/topics/security/
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Django Security Releases: https://www.djangoproject.com/weblog/
