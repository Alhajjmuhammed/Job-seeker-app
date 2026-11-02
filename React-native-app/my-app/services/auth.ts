import apiService from './api';
import pushNotificationService from './pushNotifications';

export interface User {
  id: number;
  email: string;
  firstName: string;
  lastName: string;
  userType: 'worker' | 'client' | 'admin';
  phoneNumber?: string;
  isProfileComplete?: boolean;
  profileCompletionPercentage?: number;
  // Worker-specific fields
  workerType?: 'professional' | 'non_academic';
  verificationStatus?: 'pending' | 'verified' | 'rejected';
  availability?: 'available' | 'busy' | 'offline';
  averageRating?: number;
  profileImage?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

// The API answers in three shapes: {message}, {detail} (rate limits) or a
// map of field -> [errors] (validation). Only {message} used to be read, so
// "email already used" or "too many attempts" showed as a bare "failed".
export function apiErrorMessage(error: any, fallback: string): string {
  const data = error?.response?.data;
  if (!data) {
    return error?.message === 'Network Error'
      ? 'No internet connection. Please check your connection and try again.'
      : fallback;
  }
  if (typeof data === 'string') return fallback;
  if (data.message) return data.message;
  if (data.detail) return data.detail;
  if (data.error) return data.error;
  const firstField = Object.keys(data)[0];
  if (firstField) {
    const value = data[firstField];
    const text = Array.isArray(value) ? value[0] : value;
    if (typeof text === 'string') {
      return firstField === 'non_field_errors' ? text : `${firstField}: ${text}`;
    }
  }
  return fallback;
}

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiService.login(email, password);
      return response;
    } catch (error: any) {
      throw new Error(apiErrorMessage(error, 'Login failed'));
    }
  },

  async register(userData: {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
    password: string;
    userType: 'worker' | 'client';
    workerType?: 'professional' | 'non-academic';
    agentCode?: string;
  }): Promise<AuthResponse> {
    try {
      const response = await apiService.register(userData);
      return response;
    } catch (error: any) {
      throw new Error(apiErrorMessage(error, 'Registration failed'));
    }
  },

  async logout(): Promise<void> {
    await apiService.logout(pushNotificationService.currentToken);
    pushNotificationService.currentToken = null;
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const userData = await apiService.getCurrentUser();
      
      // If user is a worker, fetch worker profile details
      if (userData.userType === 'worker') {
        try {
          const workerProfile = await apiService.getWorkerProfile();
          return {
            ...userData,
            workerType: workerProfile.worker_type,
            verificationStatus: workerProfile.verification_status,
            availability: workerProfile.availability,
            averageRating: workerProfile.average_rating,
            profileImage: workerProfile.profile_image,
            isProfileComplete: workerProfile.is_profile_complete,
            profileCompletionPercentage: workerProfile.profile_completion_percentage,
          };
        } catch (error) {
          console.error('Error fetching worker profile:', error);
          // Return basic user data if worker profile fetch fails
          return userData;
        }
      }
      
      return userData;
    } catch (error) {
      console.error('Error getting current user:', error);
      return null;
    }
  },

  async getToken(): Promise<string | null> {
    return await apiService.getToken();
  },

  async isAuthenticated(): Promise<boolean> {
    const token = await apiService.getToken();
    return !!token;
  },
};
