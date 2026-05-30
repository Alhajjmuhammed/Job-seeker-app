"""
Management command to check security configuration
Usage: python manage.py check_security
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Check security configuration and provide recommendations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--strict',
            action='store_true',
            help='Enable strict checks (fail on warnings)',
        )

    def handle(self, *args, **options):
        strict = options['strict']
        issues = []
        warnings = []
        passed = []

        self.stdout.write(self.style.HTTP_INFO('\n' + '='*60))
        self.stdout.write(self.style.HTTP_INFO('🔒 WORKER CONNECT SECURITY AUDIT'))
        self.stdout.write(self.style.HTTP_INFO('='*60 + '\n'))

        # Check 1: DEBUG mode
        if settings.DEBUG:
            issues.append('🔴 CRITICAL: DEBUG is True - MUST be False in production')
        else:
            passed.append('✅ DEBUG is False')

        # Check 2: SECRET_KEY
        if settings.SECRET_KEY == 'django-insecure-dev-key-CHANGE-THIS':
            issues.append('🔴 CRITICAL: Using default SECRET_KEY - Generate a new one!')
        elif 'django-insecure' in settings.SECRET_KEY:
            warnings.append('⚠️  WARNING: SECRET_KEY looks like a default value')
        elif len(settings.SECRET_KEY) < 50:
            warnings.append('⚠️  WARNING: SECRET_KEY is short (< 50 chars)')
        else:
            passed.append('✅ SECRET_KEY appears secure')

        # Check 3: ALLOWED_HOSTS
        if '*' in settings.ALLOWED_HOSTS:
            issues.append('🔴 CRITICAL: ALLOWED_HOSTS contains wildcard (*)')
        elif settings.ALLOWED_HOSTS == ['localhost', '127.0.0.1']:
            warnings.append('⚠️  WARNING: ALLOWED_HOSTS only has localhost - add production domain')
        else:
            passed.append('✅ ALLOWED_HOSTS configured')

        # Check 4: HTTPS/SSL
        if not getattr(settings, 'SECURE_SSL_REDIRECT', False) and not settings.DEBUG:
            warnings.append('⚠️  WARNING: SECURE_SSL_REDIRECT not enabled (use with HTTPS)')
        elif getattr(settings, 'SECURE_SSL_REDIRECT', False):
            passed.append('✅ SECURE_SSL_REDIRECT enabled')

        if not getattr(settings, 'SECURE_HSTS_SECONDS', 0) and not settings.DEBUG:
            warnings.append('⚠️  WARNING: HSTS not configured (recommended: 31536000)')
        elif getattr(settings, 'SECURE_HSTS_SECONDS', 0) > 0:
            passed.append(f'✅ HSTS configured ({settings.SECURE_HSTS_SECONDS}s)')

        # Check 5: Secure Cookies
        if not getattr(settings, 'SESSION_COOKIE_SECURE', False) and not settings.DEBUG:
            warnings.append('⚠️  WARNING: SESSION_COOKIE_SECURE not True (use with HTTPS)')
        elif getattr(settings, 'SESSION_COOKIE_SECURE', False):
            passed.append('✅ SESSION_COOKIE_SECURE enabled')

        if not getattr(settings, 'CSRF_COOKIE_SECURE', False) and not settings.DEBUG:
            warnings.append('⚠️  WARNING: CSRF_COOKIE_SECURE not True (use with HTTPS)')
        elif getattr(settings, 'CSRF_COOKIE_SECURE', False):
            passed.append('✅ CSRF_COOKIE_SECURE enabled')

        # Check 6: Database
        db_engine = settings.DATABASES['default']['ENGINE']
        if 'sqlite3' in db_engine and not settings.DEBUG:
            warnings.append('⚠️  WARNING: Using SQLite in production (use PostgreSQL)')
        elif 'postgresql' in db_engine:
            passed.append('✅ Using PostgreSQL database')

        # Check 7: Security Headers
        if not getattr(settings, 'SECURE_CONTENT_TYPE_NOSNIFF', False):
            warnings.append('⚠️  WARNING: SECURE_CONTENT_TYPE_NOSNIFF not enabled')
        else:
            passed.append('✅ SECURE_CONTENT_TYPE_NOSNIFF enabled')

        if not getattr(settings, 'SECURE_BROWSER_XSS_FILTER', False):
            warnings.append('⚠️  WARNING: SECURE_BROWSER_XSS_FILTER not enabled')
        else:
            passed.append('✅ SECURE_BROWSER_XSS_FILTER enabled')

        # Check 8: Admin URL
        if hasattr(settings, 'ADMIN_URL'):
            if settings.ADMIN_URL == 'admin/':
                warnings.append('⚠️  WARNING: Using default admin URL (consider changing)')
            else:
                passed.append('✅ Custom admin URL configured')

        # Check 9: Email backend
        email_backend = getattr(settings, 'EMAIL_BACKEND', '')
        if 'console' in email_backend and not settings.DEBUG:
            warnings.append('⚠️  WARNING: Using console email backend in production')
        elif 'smtp' in email_backend.lower():
            passed.append('✅ SMTP email backend configured')

        # Check 10: Password validators
        validators = getattr(settings, 'AUTH_PASSWORD_VALIDATORS', [])
        if len(validators) >= 4:
            passed.append(f'✅ Password validators configured ({len(validators)})')
        else:
            warnings.append(f'⚠️  WARNING: Only {len(validators)} password validators')

        # Check 11: Static files
        if not settings.DEBUG:
            static_root = getattr(settings, 'STATIC_ROOT', None)
            if not static_root:
                warnings.append('⚠️  WARNING: STATIC_ROOT not configured')
            else:
                passed.append('✅ STATIC_ROOT configured')

        # Check 12: Media files
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if media_root:
            passed.append('✅ MEDIA_ROOT configured')

        # Check 13: CSRF middleware
        middleware = getattr(settings, 'MIDDLEWARE', [])
        if 'django.middleware.csrf.CsrfViewMiddleware' in middleware:
            passed.append('✅ CSRF middleware enabled')
        else:
            issues.append('🔴 CRITICAL: CSRF middleware not found')

        # Check 14: Security middleware
        if 'django.middleware.security.SecurityMiddleware' in middleware:
            passed.append('✅ Security middleware enabled')
        else:
            warnings.append('⚠️  WARNING: Security middleware not found')

        # Check 15: Clickjacking protection
        if 'django.middleware.clickjacking.XFrameOptionsMiddleware' in middleware:
            passed.append('✅ Clickjacking protection enabled')
        else:
            warnings.append('⚠️  WARNING: Clickjacking protection not enabled')

        # Print results
        self.stdout.write(self.style.SUCCESS('\n✅ PASSED CHECKS:'))
        for item in passed:
            self.stdout.write(f'  {item}')

        if warnings:
            self.stdout.write(self.style.WARNING('\n⚠️  WARNINGS:'))
            for item in warnings:
                self.stdout.write(f'  {item}')

        if issues:
            self.stdout.write(self.style.ERROR('\n🔴 CRITICAL ISSUES:'))
            for item in issues:
                self.stdout.write(f'  {item}')

        # Summary
        self.stdout.write(self.style.HTTP_INFO('\n' + '='*60))
        self.stdout.write(self.style.HTTP_INFO('SUMMARY'))
        self.stdout.write(self.style.HTTP_INFO('='*60))
        self.stdout.write(f'✅ Passed: {len(passed)}')
        self.stdout.write(f'⚠️  Warnings: {len(warnings)}')
        self.stdout.write(f'🔴 Critical: {len(issues)}\n')

        # Recommendations
        if issues or warnings:
            self.stdout.write(self.style.HTTP_INFO('\n📋 RECOMMENDATIONS:\n'))
            
            if issues:
                self.stdout.write(self.style.ERROR('1. Fix CRITICAL issues immediately:'))
                self.stdout.write('   - Generate new SECRET_KEY')
                self.stdout.write('   - Set DEBUG=False in production .env')
                self.stdout.write('   - Configure ALLOWED_HOSTS properly\n')

            if warnings:
                self.stdout.write(self.style.WARNING('2. Address warnings before production:'))
                self.stdout.write('   - Enable HTTPS security settings')
                self.stdout.write('   - Migrate to PostgreSQL')
                self.stdout.write('   - Configure proper email backend')
                self.stdout.write('   - Review SECURITY.md for full checklist\n')

        # Production readiness score
        total_checks = len(passed) + len(warnings) + len(issues)
        score = (len(passed) / total_checks * 100) if total_checks > 0 else 0
        
        self.stdout.write(self.style.HTTP_INFO(f'\n🎯 Production Readiness Score: {score:.1f}%\n'))

        if score >= 90:
            self.stdout.write(self.style.SUCCESS('   Excellent! Ready for production with minor tweaks.\n'))
        elif score >= 70:
            self.stdout.write(self.style.WARNING('   Good progress. Address warnings before going live.\n'))
        elif score >= 50:
            self.stdout.write(self.style.WARNING('   Needs work. Fix critical issues first.\n'))
        else:
            self.stdout.write(self.style.ERROR('   Not ready for production. Major security issues detected.\n'))

        # Additional commands
        self.stdout.write(self.style.HTTP_INFO('📚 Additional Commands:\n'))
        self.stdout.write('  python manage.py check --deploy    # Django deployment check')
        self.stdout.write('  python manage.py migrate           # Apply security migrations')
        self.stdout.write('  safety check                       # Check for vulnerabilities\n')

        # Exit with error if critical issues found (in strict mode)
        if issues and strict:
            sys.exit(1)
