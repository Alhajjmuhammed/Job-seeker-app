import apiService from './api';

export interface User {
  id: number;
  email: string;
  firstName: string;
  lastName: string;
  userType: 'worker' | 'client' | 'admin';
  phoneNumber?: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    try {
      const response = await apiService.login(email, password);
      return response;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Login failed');
    }
  },

  async register(userData: {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
    password: string;
    userType: 'worker' | 'client';
  }): Promise<AuthResponse> {
    try {
      const response = await apiService.register(userData);
      return response;
    } catch (error: any) {
      throw new Error(error.response?.data?.message || 'Registration failed');
    }
  },

  async logout(): Promise<void> {
    await apiService.logout();
  },

  async getCurrentUser(): Promise<User | null> {
    try {
      const userData = await apiService.getUserData();
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
