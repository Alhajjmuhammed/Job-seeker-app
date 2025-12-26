import axios, { AxiosInstance, AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import API_CONFIG from '../config/api';

// Use centralized API configuration
const API_BASE_URL = API_CONFIG.API_URL;

// Storage keys
const TOKEN_KEY = '@auth_token';
const USER_KEY = '@user_data';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 15000, // 15 seconds timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      async (config) => {
        const token = await this.getToken();
        if (token) {
          config.headers.Authorization = `Token ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle errors
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Token expired or invalid, clear storage
          await this.clearAuth();
        }
        return Promise.reject(error);
      }
    );
  }

  // ============ Storage Methods ============
  async getToken(): Promise<string | null> {
    try {
      return await AsyncStorage.getItem(TOKEN_KEY);
    } catch (error) {
      console.error('Error getting token:', error);
      return null;
    }
  }

  async setToken(token: string): Promise<void> {
    try {
      await AsyncStorage.setItem(TOKEN_KEY, token);
    } catch (error) {
      console.error('Error setting token:', error);
    }
  }

  async getUserData(): Promise<any | null> {
    try {
      const userData = await AsyncStorage.getItem(USER_KEY);
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error('Error getting user data:', error);
      return null;
    }
  }

  async setUserData(userData: any): Promise<void> {
    try {
      await AsyncStorage.setItem(USER_KEY, JSON.stringify(userData));
    } catch (error) {
      console.error('Error setting user data:', error);
    }
  }

  async clearAuth(): Promise<void> {
    try {
      await AsyncStorage.multiRemove([TOKEN_KEY, USER_KEY]);
    } catch (error) {
      console.error('Error clearing auth:', error);
    }
  }

  // ============ Authentication Methods ============
  async login(email: string, password: string) {
    const response = await this.api.post('/auth/login/', {
      email: email,
      password,
    });
    
    if (response.data.token) {
      await this.setToken(response.data.token);
      await this.setUserData(response.data.user);
    }
    
    return response.data;
  }

  async register(userData: {
    firstName: string;
    lastName: string;
    email: string;
    phone: string;
    password: string;
    userType: 'worker' | 'client';
    workerType?: 'professional' | 'non-academic';
  }) {
    const response = await this.api.post('/auth/register/', {
      firstName: userData.firstName,
      lastName: userData.lastName,
      email: userData.email,
      phone: userData.phone,
      password: userData.password,
      userType: userData.userType,
      workerType: userData.workerType,
    });
    
    if (response.data.token) {
      await this.setToken(response.data.token);
      await this.setUserData(response.data.user);
    }
    
    return response.data;
  }

  async logout() {
    try {
      await this.api.post('/auth/logout/');
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      await this.clearAuth();
    }
  }

  async getCurrentUser() {
    const response = await this.api.get('/auth/user/');
    return response.data;
  }

  // ============ Worker Methods ============
  async getWorkerProfile() {
    const response = await this.api.get('/workers/profile/');
    return response.data;
  }

  async updateWorkerProfile(data: any) {
    // Check if data is FormData (for file uploads)
    const isFormData = data instanceof FormData;
    const config = isFormData ? {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    } : {
      headers: {
        'Content-Type': 'application/json',
      },
    };
    
    const response = await this.api.patch('/workers/profile/update/', data, config);
    return response.data;
  }

  async updateWorkerAvailability(isAvailable: boolean) {
    const response = await this.api.patch('/workers/availability/', {
      is_available: isAvailable,
    });
    return response.data;
  }

  async getDirectHireRequests() {
    const response = await this.api.get('/workers/direct-hire-requests/');
    return response.data;
  }

  async acceptDirectHireRequest(requestId: number) {
    const response = await this.api.post(`/workers/direct-hire-requests/${requestId}/accept/`);
    return response.data;
  }

  async rejectDirectHireRequest(requestId: number) {
    const response = await this.api.post(`/workers/direct-hire-requests/${requestId}/reject/`);
    return response.data;
  }

  async getWorkerJobs(status?: string) {
    const params = status ? { status } : {};
    const response = await this.api.get('/jobs/worker/jobs/', { params });
    return response.data;
  }

  async getWorkerApplications() {
    const response = await this.api.get('/jobs/worker/applications/');
    return response.data;
  }

  async applyForJob(jobId: number, coverLetter?: string) {
    const response = await this.api.post(`/jobs/${jobId}/apply/`, {
      cover_letter: coverLetter,
    });
    return response.data;
  }

  async getWorkerStats() {
    const response = await this.api.get('/workers/stats/');
    return response.data;
  }

  async getBrowseJobs(params?: { category?: string; city?: string }) {
    const response = await this.api.get('/jobs/browse/', { params });
    return response.data;
  }

  async uploadDocument(file: any, documentType: 'id' | 'cv' | 'certificate' | 'license' | 'other', title?: string) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (title) {
      formData.append('title', title);
    }

    const response = await this.api.post('/workers/documents/upload/', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getProfileCompletion() {
    const response = await this.api.get('/workers/profile/completion/');
    return response.data;
  }

  async getCategories() {
    const response = await this.api.get('/workers/categories/');
    return response.data;
  }

  // ============ Client Methods ============
  async getClientProfile() {
    const response = await this.api.get('/client/profile/');
    return response.data;
  }

  async updateClientProfile(data: any) {
    const response = await this.api.patch('/client/profile/update/', data);
    return response.data;
  }

  async getClientStats() {
    const response = await this.api.get('/client/stats/');
    return response.data;
  }

  async getFeaturedWorkers() {
    const response = await this.api.get('/client/workers/featured/');
    return response.data;
  }

  async searchWorkers(params?: {
    category?: string;
    location?: string;
    min_rating?: number;
    is_available?: boolean;
    search?: string;
  }) {
    const response = await this.api.get('/client/workers/search/', { params });
    return response.data;
  }

  async getWorkerDetail(workerId: number) {
    const response = await this.api.get(`/client/workers/${workerId}/`);
    return response.data;
  }

  async toggleFavoriteWorker(workerId: number) {
    const response = await this.api.post(`/client/workers/${workerId}/favorite/`);
    return response.data;
  }

  async getFavoriteWorkers() {
    const response = await this.api.get('/client/favorites/');
    return response.data;
  }

  async requestWorkerDirectly(workerId: number, data: {
    durationType: string;
    offeredRate: number;
  }) {
    const response = await this.api.post('/jobs/direct-hire-request/', {
      worker: workerId,
      duration_type: data.durationType,
      offered_rate: data.offeredRate,
    });
    return response.data;
  }

  async getClientJobs(status?: string) {
    const params = status ? { status } : {};
    const response = await this.api.get('/client/jobs/', { params });
    return response.data;
  }

  async getClientJobDetail(jobId: number) {
    const response = await this.api.get(`/client/jobs/${jobId}/`);
    return response.data;
  }

  async postJob(jobData: {
    title: string;
    description: string;
    category: number;
    city: string;
    location?: string;
    budget?: number;
    duration_days?: number;
    workers_needed?: number;
    urgency?: string;
  }) {
    const response = await this.api.post('/client/jobs/', jobData);
    return response.data;
  }

  async updateJob(jobId: number, jobData: any) {
    const response = await this.api.patch(`/client/jobs/${jobId}/`, jobData);
    return response.data;
  }

  async deleteJob(jobId: number) {
    const response = await this.api.delete(`/client/jobs/${jobId}/`);
    return response.data;
  }

  async getJobApplications(jobId: number) {
    const response = await this.api.get(`/client/jobs/${jobId}/applications/`);
    return response.data;
  }

  async acceptJobApplication(applicationId: number) {
    const response = await this.api.post(`/client/applications/${applicationId}/accept/`);
    return response.data;
  }

  async rejectJobApplication(applicationId: number) {
    const response = await this.api.post(`/client/applications/${applicationId}/reject/`);
    return response.data;
  }

  // ============ Common Methods ============
  async getMessages() {
    const response = await this.api.get('/messages/');
    return response.data;
  }

  async sendMessage(recipientId: number, message: string) {
    const response = await this.api.post('/messages/', {
      recipient: recipientId,
      message,
    });
    return response.data;
  }

  async getConversation(userId: number) {
    const response = await this.api.get(`/messages/conversation/${userId}/`);
    return response.data;
  }
}

// Export singleton instance
export default new ApiService();
