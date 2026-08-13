"""
File validation utilities for worker uploads
"""
import mimetypes
from django.core.exceptions import ValidationError


def _try_strong_validation(file, kind):
    """
    Try the real content-sniffing validator (worker_connect.file_validators,
    backed by python-magic). Returns True if it ran (file is already
    validated), False if it isn't available in this environment (e.g. the
    system libmagic library isn't installed) so the caller should fall back
    to the weaker header-based check below instead of failing every upload.
    """
    try:
        from worker_connect.file_validators import validate_profile_image, validate_worker_document
    except ImportError:
        return False

    validator = validate_profile_image if kind == 'image' else validate_worker_document
    validator(file)
    return True


def validate_image_file(file):
    """
    Validate that uploaded file is an actual image by checking MIME type.
    More secure than just checking file extension.
    """
    if _try_strong_validation(file, 'image'):
        return True

    # Check file size (max 5MB)
    max_size = 5 * 1024 * 1024  # 5MB in bytes
    if file.size > max_size:
        raise ValidationError(f'File size must be under 5MB. Current size: {file.size / (1024*1024):.2f}MB')
    
    # Get MIME type from file content
    # First, try using the content_type from the uploaded file
    content_type = file.content_type
    
    # Allowed MIME types for images
    allowed_mime_types = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp',
    ]
    
    if content_type not in allowed_mime_types:
        raise ValidationError(
            f'Invalid file type: {content_type}. '
            f'Allowed types: JPEG, PNG, GIF, WebP'
        )
    
    # Additional check: validate file extension matches MIME type
    allowed_extensions = {
        'image/jpeg': ['.jpg', '.jpeg'],
        'image/jpg': ['.jpg', '.jpeg'],
        'image/png': ['.png'],
        'image/gif': ['.gif'],
        'image/webp': ['.webp'],
    }
    
    file_ext = '.' + file.name.lower().split('.')[-1]
    valid_extensions = allowed_extensions.get(content_type, [])
    
    if file_ext not in valid_extensions:
        raise ValidationError(
            f'File extension {file_ext} does not match content type {content_type}'
        )
    
    return True


def validate_document_file(file):
    """
    Validate uploaded document files (for worker documents like ID, certificates)
    """
    if _try_strong_validation(file, 'document'):
        return True

    # Check file size (max 10MB for documents)
    max_size = 10 * 1024 * 1024  # 10MB
    if file.size > max_size:
        raise ValidationError(f'File size must be under 10MB. Current size: {file.size / (1024*1024):.2f}MB')
    
    # Allowed MIME types for documents
    allowed_mime_types = [
        'image/jpeg',
        'image/jpg',
        'image/png',
        'application/pdf',
    ]
    
    content_type = file.content_type
    
    if content_type not in allowed_mime_types:
        raise ValidationError(
            f'Invalid file type: {content_type}. '
            f'Allowed types: JPEG, PNG, PDF'
        )
    
    return True
