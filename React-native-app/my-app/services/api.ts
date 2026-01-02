import axios, { AxiosInstance, AxiosError } from 'axios';
import API_CONFIG from '../config/api';
import * as SecureStorage from './secureStorage';

// Use centralized API configuration
const API_BASE_URL = API_CONFIG.API_URL;

class ApiService {
  private api: AxiosInstance;
  private maxRetries = 3;
  private retryDelay = 1000; // Base retry delay in ms

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
      timeout: 15000, // 15 seconds timeout
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token and cache busting
    this.api.interceptors.request.use(
      async (config) => {
        const token = await SecureStorage.getToken();
        if (token) {
          config.headers.Authorization = `Token ${token}`;
        }
        
        // Add cache busting for GET requests to ensure fresh data
        if (config.method === 'get') {
          config.params = {
            ...config.params,
            _t: Date.now()
          };
        }
        
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle errors and retries
    this.api.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const config = error.config as any;
        
        // Check if we should retry
        if (!config || config.__retryCount >= this.maxRetries) {
          // Max retries reached or no config
          if (error.response?.status === 401) {
            await SecureStorage.clearAuth();
          }
          return Promise.reject(error);
        }

        // Only retry on network errors or 5xx server errors
        const shouldRetry = 
          !error.response || 
          (error.response.status >= 500 && error.response.status < 600);

        if (!shouldRetry) {
          if (error.response?.status === 401) {
            await SecureStorage.clearAuth();
          }
          return Promise.reject(error);
        }

        // Initialize retry count
        config.__retryCount = config.__retryCount || 0;
        config.__retryCount += 1;

        // Calculate exponential backoff delay
        const delay = this.retryDelay * Math.pow(2, config.__retryCount - 1);

        // Wait before retrying
        await new Promise(resolve => setTimeout(resolve, delay));

        // Retry the request
        return this.api(config);
      }
    );
  }

  // ============ Storage Methods (delegate to SecureStorage) ============
  async getToken(): Promise<string | null> {
    return SecureStorage.getToken();
  }

  async setToken(token: string): Promise<void> {
    return SecureStorage.setToken(token);
  }

  async getUserData(): Promise<any | null> {
    return SecureStorage.getUserData();
  }

  async setUserData(userData: any): Promise<void> {
    return SecureStorage.setUserData(userData);
  }

  async clearAuth(): Promise<void> {
    return SecureStorage.clearAuth();
  }

  // Callback for handling auth expiration (set by app to navigate to login)
  private onAuthExpired?: () => void;
  
  setOnAuthExpired(callback: () => void): void {
    this.onAuthExpired = callback;
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

  /**
   * Check if user session is still valid
   * Call this on app startup or resume
   */
  async validateSession(): Promise<boolean> {
    try {
      const token = await this.getToken();
      if (!token) {
        return false;
      }
      
      // Try to fetch current user to validate token
      const response = await this.api.get('/auth/me/');
      
      // Update stored user data with fresh data
      if (response.data) {
        await this.setUserData(response.data);
      }
      
      return true;
    } catch (error: any) {
      if (error.response?.status === 401) {
        // Token is invalid/expired
        await this.clearAuth();
        if (this.onAuthExpired) {
          this.onAuthExpired();
        }
        return false;
      }
      // Network error or other issue - don't clear auth
      throw error;
    }
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

  async getWorkerDocuments() {
    const response = await this.api.get('/workers/documents/');
    return response.data;
  }

  async deleteDocument(documentId: number) {
    const response = await this.api.delete(`/workers/documents/${documentId}/delete/`);
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

  // Alias for consistency
  async getJobDetail(jobId: number) {
    return this.getClientJobDetail(jobId);
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

  async createJobRequest(jobData: {
    title: string;
    description: string;
    budget: string;
    location: string;
    worker_id: number;
    category: string;
    startDate?: string;
  }) {
    const response = await this.api.post('/client/jobs/', {
      title: jobData.title,
      description: jobData.description,
      budget: parseFloat(jobData.budget),
      location: jobData.location,
      assigned_worker: jobData.worker_id,
      category_name: jobData.category,
      start_date: jobData.startDate,
    });
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

  async rateWorker(workerId: number, ratingData: {
    rating: number;
    review?: string;
  }) {
    const response = await this.api.post(`/client/workers/${workerId}/rate/`, ratingData);
    
    // Clear any cached data after rating submission to ensure fresh data
    this.clearCache();
    
    return response.data;
  }
  
  // Method to clear cached data (force fresh API calls)
  private clearCache() {
    // This ensures next API calls get fresh data
    this.api.defaults.headers.common['Cache-Control'] = 'no-cache';
    this.api.defaults.headers.common['Pragma'] = 'no-cache';
    
    // Reset after a short delay
    setTimeout(() => {
      delete this.api.defaults.headers.common['Cache-Control'];
      delete this.api.defaults.headers.common['Pragma'];
    }, 1000);
  }

  // ============== MESSAGING API ==============
  
  // Get all conversations (chat list)
  async getConversations() {
    const response = await this.api.get('/messages/conversations/');
    return response.data;
  }

  // Get messages with a specific user
  async getMessages(userId: number) {
    const response = await this.api.get(`/messages/${userId}/`);
    return response.data;
  }

  // Send a message to a user
  async sendMessage(recipientId: number, message: string, subject?: string) {
    const response = await this.api.post('/messages/send/', {
      recipient_id: recipientId,
      message,
      subject: subject || '',
    });
    return response.data;
  }

  // Get conversation with specific user
  async getConversation(userId: number) {
    const response = await this.api.get(`/messages/conversation/${userId}/`);
    return response.data;
  }

  // Get unread message count
  async getUnreadMessageCount() {
    const response = await this.api.get('/messages/unread/');
    return response.data;
  }

  // Mark message as read
  async markMessageAsRead(messageId: number) {
    const response = await this.api.post(`/messages/${messageId}/read/`);
    return response.data;
  }

  // Search for users to start conversation
  async searchUsers(query: string, userType?: 'worker' | 'client' | 'admin') {
    const params: any = { q: query };
    if (userType) params.type = userType;
    const response = await this.api.get('/messages/search-users/', { params });
    return response.data;
  }
}

// Export singleton instance
export default new ApiService();
