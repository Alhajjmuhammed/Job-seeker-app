/**
 * Type guards and validators for API responses
 * Ensures runtime type safety for data received from the backend
 */

// Base API response interfaces
export interface ApiResponse<T = any> {
  success?: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

// Type guards
export function isApiResponse(obj: any): obj is ApiResponse {
  return obj !== null && typeof obj === 'object';
}

export function isPaginatedResponse<T>(obj: any): obj is PaginatedResponse<T> {
  return (
    obj !== null &&
    typeof obj === 'object' &&
    typeof obj.count === 'number' &&
    (obj.next === null || typeof obj.next === 'string') &&
    (obj.previous === null || typeof obj.previous === 'string') &&
    Array.isArray(obj.results)
  );
}

// Validators for specific data types
export function validateWorker(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.id === 'number' &&
    typeof obj.name === 'string' &&
    typeof obj.category === 'string' &&
    (obj.rating === undefined || typeof obj.rating === 'number') &&
    (obj.reviews_count === undefined || typeof obj.reviews_count === 'number')
  );
}

export function validateJobRequest(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.id === 'number' &&
    typeof obj.title === 'string' &&
    typeof obj.status === 'string' &&
    (obj.budget === undefined || typeof obj.budget === 'number')
  );
}

export function validateApplication(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.id === 'number' &&
    typeof obj.status === 'string' &&
    (obj.worker === undefined || typeof obj.worker === 'number' || typeof obj.worker === 'object')
  );
}

export function validateMessage(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.id === 'number' &&
    typeof obj.content === 'string' &&
    typeof obj.timestamp === 'string' &&
    (obj.sender === undefined || typeof obj.sender === 'number' || typeof obj.sender === 'object')
  );
}

export function validateRating(obj: any): boolean {
  if (!obj || typeof obj !== 'object') return false;
  
  return (
    typeof obj.rating === 'number' &&
    obj.rating >= 1 &&
    obj.rating <= 5 &&
    (obj.review === undefined || typeof obj.review === 'string')
  );
}

// Sanitizers
export function sanitizeString(value: any): string {
  if (typeof value === 'string') return value;
  if (value === null || value === undefined) return '';
  return String(value);
}

export function sanitizeNumber(value: any, defaultValue: number = 0): number {
  const num = Number(value);
  return isNaN(num) ? defaultValue : num;
}

export function sanitizeBoolean(value: any): boolean {
  if (typeof value === 'boolean') return value;
  if (typeof value === 'string') return value.toLowerCase() === 'true';
  return Boolean(value);
}

export function sanitizeArray<T>(value: any, validator?: (item: any) => boolean): T[] {
  if (!Array.isArray(value)) return [];
  if (validator) {
    return value.filter(validator) as T[];
  }
  return value as T[];
}

// API response handler with validation
export function handleApiResponse<T>(
  response: any,
  validator?: (data: any) => boolean
): T | null {
  // Check if response is valid
  if (!isApiResponse(response)) {
    console.warn('Invalid API response format:', response);
    return null;
  }

  // Check for errors
  if (response.error || response.success === false) {
    console.error('API error:', response.error || response.message);
    throw new Error(response.error || response.message || 'Unknown API error');
  }

  // Extract data
  const data = response.data ?? response;

  // Validate data if validator provided
  if (validator && !validator(data)) {
    console.warn('Data validation failed:', data);
    return null;
  }

  return data as T;
}

// Example usage with error handling:
/*
try {
  const response = await apiService.getWorkers();
  const workers = handleApiResponse<Worker[]>(
    response, 
    (data) => Array.isArray(data) && data.every(validateWorker)
  );
  
  if (workers) {
    setWorkers(workers);
  }
} catch (error) {
  console.error('Failed to fetch workers:', error);
  Alert.alert('Error', 'Failed to load workers');
}
*/
