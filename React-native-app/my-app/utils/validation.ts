/**
 * Form validation utilities for Worker Connect mobile app.
 * Provides comprehensive client-side validation for all forms.
 */

// Validation rule types
export type ValidationRule = {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  email?: boolean;
  phone?: boolean;
  password?: boolean;
  match?: string; // Field name to match
  custom?: (value: string, formData?: Record<string, string>) => string | null;
};

export type ValidationSchema = Record<string, ValidationRule>;

export type ValidationErrors = Record<string, string>;

/**
 * Email validation regex (RFC 5322)
 */
const EMAIL_REGEX = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;

/**
 * Phone validation regex (international format)
 */
const PHONE_REGEX = /^\+?[1-9]\d{8,14}$/;

/**
 * Password strength requirements:
 * - At least 8 characters
 * - At least one uppercase letter
 * - At least one lowercase letter
 * - At least one number
 */
const PASSWORD_REQUIREMENTS = {
  minLength: 8,
  hasUppercase: /[A-Z]/,
  hasLowercase: /[a-z]/,
  hasNumber: /[0-9]/,
};

/**
 * Validate a single field value against a rule.
 */
export function validateField(
  value: string,
  rule: ValidationRule,
  fieldName: string,
  formData?: Record<string, string>
): string | null {
  const trimmedValue = value?.trim() || '';

  // Required check
  if (rule.required && !trimmedValue) {
    return `${formatFieldName(fieldName)} is required`;
  }

  // Skip other validations if empty and not required
  if (!trimmedValue && !rule.required) {
    return null;
  }

  // Min length
  if (rule.minLength && trimmedValue.length < rule.minLength) {
    return `${formatFieldName(fieldName)} must be at least ${rule.minLength} characters`;
  }

  // Max length
  if (rule.maxLength && trimmedValue.length > rule.maxLength) {
    return `${formatFieldName(fieldName)} must be at most ${rule.maxLength} characters`;
  }

  // Email validation
  if (rule.email && !EMAIL_REGEX.test(trimmedValue)) {
    return 'Please enter a valid email address';
  }

  // Phone validation
  if (rule.phone && !PHONE_REGEX.test(trimmedValue.replace(/[\s\-()]/g, ''))) {
    return 'Please enter a valid phone number';
  }

  // Password validation
  if (rule.password) {
    const passwordError = validatePassword(trimmedValue);
    if (passwordError) return passwordError;
  }

  // Pattern validation
  if (rule.pattern && !rule.pattern.test(trimmedValue)) {
    return `${formatFieldName(fieldName)} is invalid`;
  }

  // Match validation (for confirm password, etc.)
  if (rule.match && formData && trimmedValue !== formData[rule.match]) {
    return `${formatFieldName(fieldName)} does not match`;
  }

  // Custom validation
  if (rule.custom) {
    const customError = rule.custom(trimmedValue, formData);
    if (customError) return customError;
  }

  return null;
}

/**
 * Validate password strength.
 */
export function validatePassword(password: string): string | null {
  if (password.length < PASSWORD_REQUIREMENTS.minLength) {
    return `Password must be at least ${PASSWORD_REQUIREMENTS.minLength} characters`;
  }

  if (!PASSWORD_REQUIREMENTS.hasUppercase.test(password)) {
    return 'Password must contain at least one uppercase letter';
  }

  if (!PASSWORD_REQUIREMENTS.hasLowercase.test(password)) {
    return 'Password must contain at least one lowercase letter';
  }

  if (!PASSWORD_REQUIREMENTS.hasNumber.test(password)) {
    return 'Password must contain at least one number';
  }

  return null;
}

/**
 * Get password strength score (0-4).
 */
export function getPasswordStrength(password: string): {
  score: number;
  label: string;
  color: string;
} {
  let score = 0;

  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (PASSWORD_REQUIREMENTS.hasUppercase.test(password)) score++;
  if (PASSWORD_REQUIREMENTS.hasLowercase.test(password)) score++;
  if (PASSWORD_REQUIREMENTS.hasNumber.test(password)) score++;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;

  // Normalize to 0-4 scale
  const normalizedScore = Math.min(Math.floor(score * 0.67), 4);

  const labels = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];
  const colors = ['#ff4444', '#ffaa00', '#ffdd00', '#00cc44', '#00aa00'];

  return {
    score: normalizedScore,
    label: labels[normalizedScore],
    color: colors[normalizedScore],
  };
}

/**
 * Validate an entire form against a schema.
 */
export function validateForm(
  formData: Record<string, string>,
  schema: ValidationSchema
): ValidationErrors {
  const errors: ValidationErrors = {};

  for (const [fieldName, rule] of Object.entries(schema)) {
    const error = validateField(formData[fieldName] || '', rule, fieldName, formData);
    if (error) {
      errors[fieldName] = error;
    }
  }

  return errors;
}

/**
 * Check if form has any errors.
 */
export function hasErrors(errors: ValidationErrors): boolean {
  return Object.keys(errors).length > 0;
}

/**
 * Format field name for display (camelCase to Title Case).
 */
function formatFieldName(fieldName: string): string {
  return fieldName
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, (str) => str.toUpperCase())
    .trim();
}

// ============================================
// Pre-built validation schemas for common forms
// ============================================

export const LoginSchema: ValidationSchema = {
  email: {
    required: true,
    email: true,
  },
  password: {
    required: true,
    minLength: 1,
  },
};

export const RegisterSchema: ValidationSchema = {
  firstName: {
    required: true,
    minLength: 1,
    maxLength: 150,
  },
  lastName: {
    required: true,
    minLength: 1,
    maxLength: 150,
  },
  email: {
    required: true,
    email: true,
  },
  phone: {
    required: true,
    phone: true,
  },
  password: {
    required: true,
    password: true,
  },
  confirmPassword: {
    required: true,
    match: 'password',
  },
};

export const PasswordResetRequestSchema: ValidationSchema = {
  email: {
    required: true,
    email: true,
  },
};

export const PasswordResetSchema: ValidationSchema = {
  password: {
    required: true,
    password: true,
  },
  confirmPassword: {
    required: true,
    match: 'password',
  },
};

export const ChangePasswordSchema: ValidationSchema = {
  currentPassword: {
    required: true,
  },
  newPassword: {
    required: true,
    password: true,
  },
  confirmPassword: {
    required: true,
    match: 'newPassword',
  },
};

export const ProfileSchema: ValidationSchema = {
  firstName: {
    required: true,
    minLength: 1,
    maxLength: 150,
  },
  lastName: {
    required: true,
    minLength: 1,
    maxLength: 150,
  },
  phone: {
    required: true,
    phone: true,
  },
  bio: {
    maxLength: 1000,
  },
};

export const JobPostSchema: ValidationSchema = {
  title: {
    required: true,
    minLength: 5,
    maxLength: 200,
  },
  description: {
    required: true,
    minLength: 20,
    maxLength: 5000,
  },
  location: {
    required: true,
    minLength: 3,
    maxLength: 255,
  },
  city: {
    required: true,
    minLength: 2,
    maxLength: 100,
  },
  budget: {
    custom: (value) => {
      const num = parseFloat(value);
      if (isNaN(num) || num < 0) {
        return 'Budget must be a positive number';
      }
      return null;
    },
  },
  durationDays: {
    required: true,
    custom: (value) => {
      const num = parseInt(value, 10);
      if (isNaN(num) || num < 1 || num > 365) {
        return 'Duration must be between 1 and 365 days';
      }
      return null;
    },
  },
};
