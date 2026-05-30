"""
File upload validation utilities.

Validates uploaded files for:
- File type (extension and MIME type)
- File size
- Malicious content detection
"""
import os
import magic
import hashlib
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
import logging

logger = logging.getLogger('api')

# Allowed file types by category
ALLOWED_FILE_TYPES = {
    'image': {
        'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
        'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
        'max_size': 5 * 1024 * 1024,  # 5MB
    },
    'document': {
        'extensions': ['.pdf', '.doc', '.docx', '.txt'],
        'mime_types': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
        ],
        'max_size': 10 * 1024 * 1024,  # 10MB
    },
    'resume': {
        'extensions': ['.pdf', '.doc', '.docx'],
        'mime_types': [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        ],
        'max_size': 5 * 1024 * 1024,  # 5MB
    },
}

# Dangerous file signatures (magic bytes)
DANGEROUS_SIGNATURES = [
    b'MZ',  # Windows executable
    b'\x7fELF',  # Linux executable
    b'#!/',  # Shell script
    b'<?php',  # PHP script
    b'<script',  # JavaScript
    b'<%',  # ASP/JSP
]


def get_file_extension(filename):
    """Get lowercase file extension from filename."""
    return os.path.splitext(filename)[1].lower()


def get_mime_type(file):
    """Get MIME type of file using python-magic."""
    try:
        # Read first 2048 bytes for MIME detection
        file.seek(0)
        header = file.read(2048)
        file.seek(0)
        
        mime = magic.Magic(mime=True)
        return mime.from_buffer(header)
    except Exception as e:
        logger.warning(f"Could not detect MIME type: {e}")
        return None


def check_dangerous_content(file):
    """Check for dangerous file signatures."""
    try:
        file.seek(0)
        header = file.read(256)
        file.seek(0)
        
        for sig in DANGEROUS_SIGNATURES:
            if header.startswith(sig) or sig in header[:100]:
                return True
        return False
    except Exception as e:
        logger.warning(f"Could not check file content: {e}")
        return True  # Reject if we can't check


def calculate_file_hash(file):
    """Calculate SHA256 hash of file for tracking/deduplication."""
    sha256_hash = hashlib.sha256()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b""):
        sha256_hash.update(chunk)
    file.seek(0)
    return sha256_hash.hexdigest()


class FileValidator:
    """
    Comprehensive file validator for uploads.
    
    Usage:
        validator = FileValidator(file_type='image')
        validator(uploaded_file)  # Raises ValidationError if invalid
    """
    
    def __init__(self, file_type='document', custom_extensions=None, 
                 custom_mime_types=None, max_size=None):
        """
        Initialize validator.
        
        Args:
            file_type: One of 'image', 'document', 'resume'
            custom_extensions: Override allowed extensions
            custom_mime_types: Override allowed MIME types
            max_size: Override max file size in bytes
        """
        self.file_type = file_type
        config = ALLOWED_FILE_TYPES.get(file_type, ALLOWED_FILE_TYPES['document'])
        
        self.allowed_extensions = custom_extensions or config['extensions']
        self.allowed_mime_types = custom_mime_types or config['mime_types']
        self.max_size = max_size or config['max_size']
    
    def __call__(self, file):
        """Validate the uploaded file."""
        if not isinstance(file, UploadedFile):
            raise ValidationError("Invalid file object")
        
        self.validate_extension(file)
        self.validate_size(file)
        self.validate_mime_type(file)
        self.validate_content(file)
        
        return True
    
    def validate_extension(self, file):
        """Validate file extension."""
        ext = get_file_extension(file.name)
        if ext not in self.allowed_extensions:
            raise ValidationError(
                f"File type '{ext}' is not allowed. "
                f"Allowed types: {', '.join(self.allowed_extensions)}"
            )
    
    def validate_size(self, file):
        """Validate file size."""
        if file.size > self.max_size:
            max_mb = self.max_size / (1024 * 1024)
            raise ValidationError(
                f"File size ({file.size / (1024*1024):.1f}MB) exceeds "
                f"maximum allowed size ({max_mb:.1f}MB)"
            )
    
    def validate_mime_type(self, file):
        """Validate MIME type matches extension."""
        mime_type = get_mime_type(file)
        if mime_type and mime_type not in self.allowed_mime_types:
            raise ValidationError(
                f"File content type '{mime_type}' does not match "
                f"allowed types for {self.file_type} files"
            )
    
    def validate_content(self, file):
        """Check for dangerous content."""
        if check_dangerous_content(file):
            logger.warning(
                f"Potentially dangerous file upload blocked: {file.name}"
            )
            raise ValidationError(
                "File appears to contain executable or script content"
            )


# Pre-configured validators
validate_image = FileValidator(file_type='image')
validate_document = FileValidator(file_type='document')
validate_resume = FileValidator(file_type='resume')


def validate_profile_image(file):
    """Validate profile image upload."""
    validator = FileValidator(
        file_type='image',
        max_size=2 * 1024 * 1024  # 2MB for profile images
    )
    return validator(file)


def validate_worker_document(file):
    """Validate worker document upload (ID, certificates, etc.)."""
    validator = FileValidator(
        file_type='document',
        max_size=10 * 1024 * 1024  # 10MB
    )
    return validator(file)


def sanitize_filename(filename):
    """
    Sanitize filename to prevent directory traversal and other issues.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    import uuid
    
    # Get extension
    ext = get_file_extension(filename)
    
    # Remove path components
    filename = os.path.basename(filename)
    
    # Remove non-alphanumeric characters except dots, dashes, underscores
    name = os.path.splitext(filename)[0]
    name = re.sub(r'[^\w\-.]', '_', name)
    
    # Truncate if too long
    if len(name) > 100:
        name = name[:100]
    
    # Add unique suffix to prevent collisions
    unique_suffix = uuid.uuid4().hex[:8]
    
    return f"{name}_{unique_suffix}{ext}"
