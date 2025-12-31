import { useState, useCallback, useMemo } from 'react';
import {
  ValidationSchema,
  ValidationErrors,
  validateForm,
  validateField,
  hasErrors,
} from './validation';

/**
 * Custom hook for form validation in React Native.
 * Provides real-time validation and form state management.
 */
export function useFormValidation<T extends Record<string, string>>(
  initialValues: T,
  schema: ValidationSchema
) {
  const [values, setValues] = useState<T>(initialValues);
  const [errors, setErrors] = useState<ValidationErrors>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * Update a single field value.
   */
  const setValue = useCallback(
    (field: keyof T, value: string) => {
      setValues((prev) => ({ ...prev, [field]: value }));

      // Validate on change if field was touched
      if (touched[field as string]) {
        const fieldSchema = schema[field as string];
        if (fieldSchema) {
          const error = validateField(value, fieldSchema, field as string, values);
          setErrors((prev) => {
            if (error) {
              return { ...prev, [field]: error };
            }
            const newErrors = { ...prev };
            delete newErrors[field as string];
            return newErrors;
          });
        }
      }
    },
    [schema, touched, values]
  );

  /**
   * Mark a field as touched (for showing errors after user interaction).
   */
  const setFieldTouched = useCallback(
    (field: keyof T) => {
      setTouched((prev) => ({ ...prev, [field]: true }));

      // Validate when field is touched
      const fieldSchema = schema[field as string];
      if (fieldSchema) {
        const error = validateField(
          values[field],
          fieldSchema,
          field as string,
          values
        );
        if (error) {
          setErrors((prev) => ({ ...prev, [field]: error }));
        }
      }
    },
    [schema, values]
  );

  /**
   * Validate all fields.
   */
  const validateAll = useCallback(() => {
    const allErrors = validateForm(values, schema);
    setErrors(allErrors);
    // Mark all fields as touched
    const allTouched = Object.keys(schema).reduce(
      (acc, key) => ({ ...acc, [key]: true }),
      {}
    );
    setTouched(allTouched);
    return !hasErrors(allErrors);
  }, [values, schema]);

  /**
   * Reset form to initial values.
   */
  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
    setIsSubmitting(false);
  }, [initialValues]);

  /**
   * Handle form submission.
   */
  const handleSubmit = useCallback(
    async (onSubmit: (values: T) => Promise<void>) => {
      setIsSubmitting(true);

      const isValid = validateAll();
      if (!isValid) {
        setIsSubmitting(false);
        return false;
      }

      try {
        await onSubmit(values);
        return true;
      } catch (error) {
        // Handle API validation errors
        if (error && typeof error === 'object' && 'fieldErrors' in error) {
          setErrors(error.fieldErrors as ValidationErrors);
        }
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    [validateAll, values]
  );

  /**
   * Get props for TextInput components.
   */
  const getFieldProps = useCallback(
    (field: keyof T) => ({
      value: values[field],
      onChangeText: (text: string) => setValue(field, text),
      onBlur: () => setFieldTouched(field),
    }),
    [values, setValue, setFieldTouched]
  );

  /**
   * Check if form is valid.
   */
  const isValid = useMemo(() => {
    const allErrors = validateForm(values, schema);
    return !hasErrors(allErrors);
  }, [values, schema]);

  /**
   * Check if a specific field has an error after being touched.
   */
  const getFieldError = useCallback(
    (field: keyof T): string | undefined => {
      if (touched[field as string]) {
        return errors[field as string];
      }
      return undefined;
    },
    [errors, touched]
  );

  return {
    values,
    errors,
    touched,
    isSubmitting,
    isValid,
    setValue,
    setFieldTouched,
    validateAll,
    reset,
    handleSubmit,
    getFieldProps,
    getFieldError,
    setValues,
    setErrors,
  };
}

export default useFormValidation;
