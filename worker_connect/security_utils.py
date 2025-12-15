"""
Security utilities for Worker Connect
Provides input validation, sanitization, and security helpers
"""

import re
import os
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags
from django.core.validators import FileExtensionValidator


# Allowed file extensions
ALLOWED_DOCUMENT_EXTENSIONS = ['pdf', 'doc', 'docx', 'txt']
ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
ALLOWED_CERTIFICATE_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']

# Maximum file sizes (in bytes)
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB


def validate_file_extension(file, allowed_extensions):
    """
    Validate that uploaded file has an allowed extension.
    
    Args:
        file: UploadedFile object
        allowed_extensions: List of allowed extensions (without dot)
    
    Raises:
        ValidationError: If file extension is not allowed
    """
    ext = os.path.splitext(file.name)[1][1:].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'File type .{ext} is not allowed. Allowed types: {", ".join(allowed_extensions)}'
        )


def validate_file_size(file, max_size):
    """
    Validate that uploaded file is within size limit.
    
    Args:
        file: UploadedFile object
        max_size: Maximum size in bytes
    
    Raises:
        ValidationError: If file is too large
    """
    if file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f'File size must be under {max_mb:.1f}MB. Your file is {file.size / (1024 * 1024):.1f}MB'
        )


def validate_document_file(file):
    """
    Validate document upload (CV, certificates, etc.)
    
    Args:
        file: UploadedFile object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_extension(file, ALLOWED_DOCUMENT_EXTENSIONS)
    validate_file_size(file, MAX_DOCUMENT_SIZE)


def validate_image_file(file):
    """
    Validate image upload (profile pictures, etc.)
    
    Args:
        file: UploadedFile object
    
    Raises:
        ValidationError: If validation fails
    """
    validate_file_extension(file, ALLOWED_IMAGE_EXTENSIONS)
    validate_file_size(file, MAX_IMAGE_SIZE)


def sanitize_html(text, allowed_tags=None):
    """
    Sanitize HTML input to prevent XSS attacks.
    
    Args:
        text: Input text that may contain HTML
        allowed_tags: List of allowed HTML tags (default: None = strip all)
    
    Returns:
        Sanitized text
    """
    if allowed_tags is None:
        # Strip all HTML tags
        return strip_tags(text)
    
    # For more advanced sanitization, use bleach library
    # pip install bleach
    # import bleach
    # return bleach.clean(text, tags=allowed_tags, strip=True)
    
    # Basic implementation - strip all tags by default
    return strip_tags(text)


def validate_phone_number(phone):
    """
    Validate phone number format.
    
    Args:
        phone: Phone number string
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid format
    """
    # International format: +XXX XXXXXXXXX
    pattern = r'^\+?1?\d{9,15}$'
    if not re.match(pattern, phone.replace(' ', '').replace('-', '')):
        raise ValidationError(
            'Invalid phone number format. Use: +XXX XXXXXXXXX'
        )
    return True


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal attacks.
    
    Args:
        filename: Original filename
    
    Returns:
        Safe filename
    """
    # Remove path separators and special characters
    filename = os.path.basename(filename)
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return name + ext


def validate_url(url):
    """
    Validate URL to prevent SSRF attacks.
    
    Args:
        url: URL string
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If invalid or suspicious URL
    """
    # Block localhost and private IP ranges
    blocked_patterns = [
        r'localhost',
        r'127\.0\.0\.1',
        r'0\.0\.0\.0',
        r'192\.168\.',
        r'10\.',
        r'172\.(1[6-9]|2[0-9]|3[0-1])\.',
    ]
    
    for pattern in blocked_patterns:
        if re.search(pattern, url.lower()):
            raise ValidationError('URL points to a restricted address')
    
    return True


def mask_sensitive_data(text, mask_char='*'):
    """
    Mask sensitive data for logging.
    
    Args:
        text: Text containing sensitive data
        mask_char: Character to use for masking
    
    Returns:
        Masked text
    """
    # Mask email addresses
    text = re.sub(
        r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
        r'\1***@\2',
        text
    )
    
    # Mask phone numbers
    text = re.sub(
        r'(\+?\d{1,3}[\s-]?)(\d{3})[\s-]?(\d{3})[\s-]?(\d{4})',
        r'\1***-***-\4',
        text
    )
    
    return text


def check_password_strength(password):
    """
    Check password strength beyond Django's default validators.
    
    Args:
        password: Password string
    
    Returns:
        dict: {
            'is_strong': bool,
            'score': int (0-5),
            'feedback': list of strings
        }
    """
    score = 0
    feedback = []
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append('Password should be at least 8 characters long')
    
    if len(password) >= 12:
        score += 1
    
    # Complexity checks
    if re.search(r'[a-z]', password):
        score += 1
    else:
        feedback.append('Add lowercase letters')
    
    if re.search(r'[A-Z]', password):
        score += 1
    else:
        feedback.append('Add uppercase letters')
    
    if re.search(r'\d', password):
        score += 1
    else:
        feedback.append('Add numbers')
    
    if re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        score += 1
    else:
        feedback.append('Add special characters')
    
    # Check for common patterns
    common_patterns = ['12345', 'qwerty', 'password', 'admin']
    if any(pattern in password.lower() for pattern in common_patterns):
        score -= 1
        feedback.append('Avoid common patterns')
    
    is_strong = score >= 4
    
    return {
        'is_strong': is_strong,
        'score': max(0, score),
        'feedback': feedback
    }


def rate_limit_key(request, identifier='default'):
    """
    Generate a rate limit key based on user IP and identifier.
    
    Args:
        request: Django request object
        identifier: Unique identifier for the action
    
    Returns:
        str: Rate limit key
    """
    ip_address = get_client_ip(request)
    return f'ratelimit:{identifier}:{ip_address}'


def get_client_ip(request):
    """
    Get client IP address from request, handling proxies.
    
    Args:
        request: Django request object
    
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# File type detection using magic numbers
FILE_SIGNATURES = {
    'pdf': [b'%PDF'],
    'jpg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG\r\n\x1a\n'],
    'gif': [b'GIF87a', b'GIF89a'],
    'docx': [b'PK\x03\x04'],
}


def validate_file_content(file):
    """
    Validate file content by checking magic numbers (file signature).
    This prevents file type spoofing.
    
    Args:
        file: UploadedFile object
    
    Returns:
        bool: True if file content matches declared extension
    
    Raises:
        ValidationError: If file content doesn't match extension
    """
    # Get file extension
    ext = os.path.splitext(file.name)[1][1:].lower()
    
    # Read first 8 bytes to check signature
    file.seek(0)
    header = file.read(8)
    file.seek(0)  # Reset file pointer
    
    if ext in FILE_SIGNATURES:
        signatures = FILE_SIGNATURES[ext]
        if not any(header.startswith(sig) for sig in signatures):
            raise ValidationError(
                f'File content does not match extension .{ext}. Possible file type spoofing.'
            )
    
    return True


# SQL Injection Prevention (when using raw queries - not recommended)
def escape_sql_identifier(identifier):
    """
    Escape SQL identifier (table/column name).
    Note: Use Django ORM instead of raw SQL when possible!
    
    Args:
        identifier: SQL identifier string
    
    Returns:
        Escaped identifier
    """
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identifier):
        raise ValueError('Invalid SQL identifier')
    return identifier


# CSRF Token validation for AJAX requests
def validate_ajax_csrf(request):
    """
    Validate CSRF token for AJAX requests.
    
    Args:
        request: Django request object
    
    Returns:
        bool: True if valid
    
    Raises:
        ValidationError: If CSRF validation fails
    """
    from django.middleware.csrf import CsrfViewMiddleware
    
    reason = CsrfViewMiddleware().process_view(request, None, (), {})
    if reason:
        raise ValidationError('CSRF validation failed')
    return True
