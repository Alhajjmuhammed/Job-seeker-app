# 🔒 Security Quick Reference Card

## Emergency Commands

```bash
# Security audit (run regularly)
python manage.py check_security

# Django deployment check
python manage.py check --deploy

# Check for vulnerable dependencies
pip list --outdated
safety check  # Install with: pip install safety

# Generate new SECRET_KEY
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

---

## Critical Settings (.env file)

```env
# MUST CHANGE FOR PRODUCTION
DEBUG=False
SECRET_KEY=<generate-new-key-here>
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# HTTPS Security (enable when using SSL)
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

---

## Security Features Enabled

✅ **Authentication & Authorization**
- Custom User model with role-based access
- @login_required decorators on all protected views
- @staff_member_required for admin panel
- Strong password validation (4 validators)

✅ **CSRF Protection**
- CsrfViewMiddleware enabled
- CSRF tokens in all forms
- CSRF_COOKIE_HTTPONLY = True

✅ **XSS Prevention**
- Django auto-escaping in templates
- SECURE_BROWSER_XSS_FILTER = True
- HTML sanitization utilities available

✅ **SQL Injection Prevention**
- Django ORM (no raw SQL)
- Parameterized queries throughout

✅ **Clickjacking Protection**
- X_FRAME_OPTIONS = 'DENY'
- XFrameOptionsMiddleware enabled

✅ **File Upload Security**
- Extension validation
- Size limits (5MB/10MB)
- Content verification
- Filename sanitization

✅ **Session Security**
- 24-hour timeout
- Secure cookies (HTTPS)
- HTTPOnly cookies

✅ **Database Indexes**
- Performance optimizations
- DOS attack prevention

---

## Security Utilities Available

```python
# Import security utilities
from worker_connect.security_utils import (
    validate_document_file,
    validate_image_file,
    sanitize_html,
    validate_phone_number,
    sanitize_filename,
    check_password_strength,
    get_client_ip,
)

# Example usage
try:
    validate_document_file(uploaded_file)
    validate_image_file(profile_pic)
    clean_text = sanitize_html(user_input)
    validate_phone_number(phone)
except ValidationError as e:
    # Handle validation error
    pass
```

---

## Common Security Tasks

### Change SECRET_KEY
```bash
# 1. Generate new key
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# 2. Update .env file
SECRET_KEY=<new-key>

# 3. Restart server (all users will be logged out)
```

### Enable HTTPS
```bash
# 1. Get SSL certificate (Let's Encrypt)
sudo certbot --nginx -d yourdomain.com

# 2. Update .env
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True

# 3. Restart server
```

### Check Security Status
```bash
# Run security audit
python manage.py check_security

# Sample output:
# ✅ Passed: 12
# ⚠️  Warnings: 3
# 🔴 Critical: 0
# 🎯 Production Readiness: 85%
```

### Install Pre-Commit Hook
```bash
# Prevent committing secrets
cp pre-commit-security-check.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

---

## File Upload Validation

```python
# In your forms
from worker_connect.security_utils import validate_document_file

def clean_file(self):
    file = self.cleaned_data.get('file')
    if file:
        validate_document_file(file)  # Raises ValidationError if invalid
    return file
```

---

## Rate Limiting (Recommended Add-on)

```bash
# Install
pip install django-axes

# Add to INSTALLED_APPS
INSTALLED_APPS += ['axes']

# Configure in settings.py
AXES_FAILURE_LIMIT = 5  # Lock after 5 attempts
AXES_COOLOFF_TIME = 1   # Lock for 1 hour
```

---

## Monitoring Setup

```bash
# Install Sentry (error tracking)
pip install sentry-sdk

# Configure in settings.py
import sentry_sdk
sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
)
```

---

## Security Checklist

**Before Production:**
- [ ] DEBUG=False
- [ ] Strong SECRET_KEY
- [ ] ALLOWED_HOSTS configured
- [ ] HTTPS enabled
- [ ] PostgreSQL (not SQLite)
- [ ] Secure cookies enabled
- [ ] HSTS configured
- [ ] Email configured
- [ ] Static files collected
- [ ] Logs directory created
- [ ] Backup strategy
- [ ] Monitoring enabled

**Monthly:**
- [ ] Update dependencies
- [ ] Check security logs
- [ ] Run security audit
- [ ] Review user permissions
- [ ] Test backups

**Immediately if Breach:**
1. Take site offline
2. Change SECRET_KEY
3. Reset admin passwords
4. Review logs
5. Patch vulnerability
6. Notify affected users

---

## Quick Links

- Full Guide: `SECURITY.md`
- Setup Script: `./setup_security.sh`
- Audit: `python manage.py check_security`
- Django Docs: https://docs.djangoproject.com/en/4.2/topics/security/

---

**Keep this card handy for quick reference!**

Last updated: December 15, 2025
