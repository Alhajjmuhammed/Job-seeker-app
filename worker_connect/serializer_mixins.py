"""
Serializer mixins for common functionality.
"""
from rest_framework import serializers
from django.utils.html import strip_tags
import re


class SanitizedCharField(serializers.CharField):
    """CharField that automatically sanitizes HTML/script tags"""
    
    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if value:
            # Strip HTML tags
            value = strip_tags(value)
            # Remove potential script injections
            value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
            value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
        return value


class SanitizedTextField(SanitizedCharField):
    """TextField that automatically sanitizes HTML/script tags"""
    pass


class SanitizedSerializerMixin:
    """
    Mixin that automatically sanitizes text fields to prevent XSS.
    Add to serializers that accept user input with text fields.
    """
    
    # Fields to sanitize (override in subclass if needed)
    sanitize_fields = []
    
    def to_internal_value(self, data):
        """Sanitize specified fields before validation"""
        if isinstance(data, dict):
            sanitized_data = data.copy()
            
            # Get fields to sanitize from class or auto-detect CharField/TextField
            fields_to_sanitize = self.sanitize_fields or self._get_text_fields()
            
            for field_name in fields_to_sanitize:
                if field_name in sanitized_data and sanitized_data[field_name]:
                    value = sanitized_data[field_name]
                    if isinstance(value, str):
                        # Strip HTML tags
                        value = strip_tags(value)
                        # Remove potential script injections
                        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
                        value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
                        sanitized_data[field_name] = value
            
            return super().to_internal_value(sanitized_data)
        
        return super().to_internal_value(data)
    
    def _get_text_fields(self):
        """Auto-detect text fields that should be sanitized"""
        text_fields = []
        for field_name, field in self.fields.items():
            if isinstance(field, (serializers.CharField,)):
                text_fields.append(field_name)
        return text_fields


def sanitize_string(value):
    """
    Utility function to sanitize a single string value.
    
    Args:
        value: String to sanitize
    
    Returns:
        Sanitized string
    """
    if not value or not isinstance(value, str):
        return value
    
    # Strip HTML tags
    value = strip_tags(value)
    # Remove potential script injections
    value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
    value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
    
    return value
