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

  // ============ Password Management Methods ============
  async requestPasswordReset(email: string) {
    const response = await this.api.post('/auth/password-reset/', {
      email: email,
    });
    return response.data;
  }

  async confirmPasswordReset(token: string, password: string) {
    const response = await this.api.post('/auth/password-reset/confirm/', {
      token: token,
      password: password,
    });
    return response.data;
  }

  async changePassword(currentPassword: string, newPassword: string) {
    const response = await this.api.post('/auth/change-password/', {
      current_password: currentPassword,
      new_password: newPassword,
    });
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

  async applyForJob(jobId: number, coverLetter?: string, proposedRate?: number) {
    const response = await this.api.post(`/jobs/worker/jobs/${jobId}/apply/`, {
      cover_letter: coverLetter,
      proposed_rate: proposedRate,
    });
    return response.data;
  }

  async getWorkerStats() {
    const response = await this.api.get('/workers/stats/');
    return response.data;
  }

  async getAssignedJobs() {
    const response = await this.api.get('/workers/assigned-jobs/');
    return response.data;
  }

  async updateJobStatus(jobId: number, status: string) {
    const response = await this.api.patch(`/workers/assigned-jobs/${jobId}/status/`, { status });
    return response.data;
  }

  async getBrowseJobs(params?: { category?: string; city?: string }) {
    const response = await this.api.get('/jobs/browse/', { params });
    return response.data;
  }

  async getSavedJobs(includeClosed: boolean = false) {
    const response = await this.api.get('/jobs/saved/', { 
      params: { include_closed: includeClosed } 
    });
    return response.data;
  }

  async saveJob(jobId: number) {
    const response = await this.api.post(`/jobs/${jobId}/save/`);
    return response.data;
  }

  async unsaveJob(jobId: number) {
    const response = await this.api.delete(`/jobs/${jobId}/unsave/`);
    return response.data;
  }

  async isJobSaved(jobId: number) {
    const response = await this.api.get(`/jobs/${jobId}/is-saved/`);
    return response.data;
  }

  async registerPushToken(token: string, platform: string) {
    const response = await this.api.post('/notifications/register-token/', {
      token,
      platform,
      device_type: platform === 'ios' ? 'apns' : 'fcm',
    });
    return response.data;
  }

  async getNotifications(unreadOnly: boolean = false) {
    const response = await this.api.get('/notifications/', {
      params: { unread_only: unreadOnly }
    });
    return response.data;
  }

  async markNotificationAsRead(notificationId: number) {
    const response = await this.api.post(`/notifications/${notificationId}/read/`);
    return response.data;
  }

  async markAllNotificationsAsRead() {
    const response = await this.api.post('/notifications/mark-all-read/');
    return response.data;
  }

  async getUnreadNotificationCount() {
    const response = await this.api.get('/notifications/unread-count/');
    return response.data;
  }

  async getWorkerAnalytics() {
    const response = await this.api.get('/workers/analytics/');
    return response.data;
  }

  async getEarningsBreakdown(groupBy: 'month' | 'week' = 'month', periods: number = 6) {
    const response = await this.api.get('/workers/earnings/breakdown/', {
      params: { group_by: groupBy, periods }
    });
    return response.data;
  }

  async getEarningsByCategory() {
    const response = await this.api.get('/workers/earnings/by-category/');
    return response.data;
  }

  async getTopClients(limit: number = 10) {
    const response = await this.api.get('/workers/earnings/top-clients/', {
      params: { limit }
    });
    return response.data;
  }

  async getPaymentHistory(limit: number = 50) {
    const response = await this.api.get('/workers/earnings/payment-history/', {
      params: { limit }
    });
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

  async getSkills(categoryIds?: number[]) {
    const params = categoryIds && categoryIds.length > 0 
      ? { categories: categoryIds.join(',') }
      : {};
    const response = await this.api.get('/workers/skills/', { params });
    return response.data;
  }

  async getWorkExperiences() {
    const response = await this.api.get('/workers/experiences/');
    return response.data;
  }

  async addWorkExperience(data: any) {
    const response = await this.api.post('/workers/experiences/', data);
    return response.data;
  }

  async updateWorkExperience(experienceId: number, data: any) {
    const response = await this.api.patch(`/workers/experiences/${experienceId}/`, data);
    return response.data;
  }

  async deleteWorkExperience(experienceId: number) {
    const response = await this.api.delete(`/workers/experiences/${experienceId}/`);
    return response.data;
  }

  // ============ Client Methods ============
  async getClientProfile() {
    const response = await this.api.get('/clients/profile/');
    return response.data;
  }

  async updateClientProfile(data: any) {
    const response = await this.api.patch('/clients/profile/update/', data);
    return response.data;
  }

  async getClientStats() {
    const response = await this.api.get('/clients/stats/');
    return response.data;
  }

  // ============ FAVORITES ============
  async getFavorites(page: number = 1) {
    const response = await this.api.get(`/clients/favorites/?page=${page}`);
    return response.data;
  }

  async toggleFavorite(workerId: number) {
    const response = await this.api.post(`/clients/favorites/toggle/${workerId}/`);
    return response.data;
  }

  // ============ SERVICE-BASED METHODS (No worker browsing) ============
  async getServices() {
    const response = await this.api.get('/clients/services/');
    return response.data;
  }

  // Get featured workers for client dashboard
  async getFeaturedWorkers() {
    const response = await this.api.get('/workers/featured/');
    return response.data;
  }

  // NEW: Calculate service price based on duration
  async calculatePrice(data: {
    category_id: number;
    duration_type: 'daily' | 'monthly' | '3_months' | '6_months' | 'year ly' | 'custom';
    service_start_date?: string;
    service_end_date?: string;
  }) {
    const response = await this.api.post('/v1/clients/calculate-price/', data);
    return response.data;
  }

  // NEW: Process payment (Card or M-Pesa)
  async processPayment(data: {
    amount: number;
    payment_type: 'card' | 'mpesa';
    // For Card payments:
    card_number?: string;
    card_holder?: string;
    card_expiry?: string;
    card_cvv?: string;
    // For M-Pesa payments:
    phone_number?: string;
  }) {
    const response = await this.api.post('/v1/clients/process-payment/', data);
    return response.data;
  }

  // NEW: Get category pricing
  async getCategoryPricing() {
    const response = await this.api.get('/v1/clients/category-pricing/');
    return response.data;
  }

  async requestService(categoryId: number, data: {
    title: string;
    description: string;
    location: string;
    city: string;
    preferred_date?: string;
    preferred_time?: string;
    duration_type: 'daily' | 'monthly' | '3_months' | '6_months' | 'yearly' | 'custom';
    service_start_date?: string;
    service_end_date?: string;
    workers_needed?: number;
    urgency?: string;
    client_notes?: string;
    payment_transaction_id?: string;
    payment_method?: string;
  } | FormData) {
    // Handle FormData (for file uploads like payment screenshot)
    if (data instanceof FormData) {
      const response = await this.api.post(`/v1/clients/services/${categoryId}/request/`, data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    }
    
    // Handle regular object data
    const response = await this.api.post(`/v1/clients/services/${categoryId}/request/`, {
      ...data,
    });
    return response.data;
  }

  async getMyServiceRequests(page: number = 1, category?: string, fromDate?: string, toDate?: string, search?: string) {
    const params: any = { page };
    if (category) params.category = category;
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;
    if (search) params.search = search;
    
    const response = await this.api.get('/v1/clients/requests/', { params });
    return response.data;
  }

  async getServiceRequestDetail(requestId: number) {
    const response = await this.api.get(`/v1/clients/requests/${requestId}/`);
    return response.data;
  }

  async cancelServiceRequest(requestId: number) {
    const response = await this.api.post(`/v1/clients/requests/${requestId}/cancel/`);
    return response.data;
  }

  async completeServiceRequest(requestId: number) {
    const response = await this.api.post(`/v1/clients/requests/${requestId}/complete/`);
    return response.data;
  }

  async updateServiceRequest(requestId: number, data: any) {
    // Support both JSON and FormData
    const config = data instanceof FormData ? {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    } : {};
    
    const response = await this.api.put(`/v1/clients/requests/${requestId}/update/`, data, config);
    return response.data;
  }

  async getClientStatistics() {
    const response = await this.api.get('/v1/clients/stats/');
    return response.data;
  }

  async getClientCategories() {
    const response = await this.api.get('/v1/clients/categories/');
    return response.data;
  }

  // ============ WORKER SERVICE REQUEST API ============
  // NEW: Using multi-worker assignment endpoints
  async getWorkerAssignments(status?: string) {
    const params = status ? { status } : {};
    const response = await this.api.get('/v1/worker/my-assignments/', { params });
    return response.data;
  }

  async getWorkerAssignmentDetail(assignmentId: number) {
    const response = await this.api.get(`/v1/worker/my-assignments/${assignmentId}/`);
    return response.data;
  }

  async getPendingAssignments() {
    const response = await this.api.get('/v1/worker/my-assignments/pending/');
    return response.data;
  }

  async getCurrentAssignment() {
    // Get assignments filtered by in_progress status
    const response = await this.api.get('/v1/worker/my-assignments/', { 
      params: { status: 'in_progress' } 
    });
    return response.data;
  }

  async acceptAssignment(assignmentId: number, notes?: string) {
    const response = await this.api.post(
      `/v1/worker/my-assignments/${assignmentId}/respond/`,
      { accepted: true, notes }
    );
    return response.data;
  }

  async rejectAssignment(assignmentId: number, reason: string) {
    const response = await this.api.post(
      `/v1/worker/my-assignments/${assignmentId}/respond/`,
      { accepted: false, rejection_reason: reason }
    );
    return response.data;
  }

  async clockIn(assignmentId: number, location?: { latitude: number; longitude: number }) {
    const response = await this.api.post(
      `/v1/worker/my-assignments/${assignmentId}/clock-in/`,
      { location: location ? `${location.latitude},${location.longitude}` : undefined }
    );
    return response.data;
  }

  async clockOut(assignmentId: number, location?: { latitude: number; longitude: number }, notes?: string) {
    const response = await this.api.post(
      `/v1/worker/my-assignments/${assignmentId}/clock-out/`,
      { 
        location: location ? `${location.latitude},${location.longitude}` : undefined,
        notes 
      }
    );
    return response.data;
  }

  async completeService(assignmentId: number, completionNotes: string) {
    const response = await this.api.post(
      `/v1/worker/my-assignments/${assignmentId}/complete/`,
      { completion_notes: completionNotes }
    );
    return response.data;
  }

  async getWorkerActivity() {
    const response = await this.api.get('/v1/worker/activity/');
    return response.data;
  }

  async getWorkerStatistics() {
    // NEW: Using multi-worker assignment stats endpoint
    const response = await this.api.get('/v1/worker/my-assignments/stats/');
    return response.data;
  }

  // ============ JOB MANAGEMENT ============
  async getClientJobs(status?: string) {
    const params = status ? { status } : {};
    const response = await this.api.get('/clients/jobs/', { params });
    return response.data;
  }

  async getClientJobDetail(jobId: number) {
    const response = await this.api.get(`/clients/jobs/${jobId}/`);
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
    const response = await this.api.post('/clients/jobs/', jobData);
    return response.data;
  }

  async updateJob(jobId: number, jobData: any) {
    const response = await this.api.patch(`/clients/jobs/${jobId}/`, jobData);
    return response.data;
  }

  async deleteJob(jobId: number) {
    const response = await this.api.delete(`/clients/jobs/${jobId}/`);
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
    const response = await this.api.post('/clients/jobs/', {
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
    const response = await this.api.get(`/clients/jobs/${jobId}/applications/`);
    return response.data;
  }

  async acceptJobApplication(applicationId: number) {
    const response = await this.api.post(`/clients/applications/${applicationId}/accept/`);
    return response.data;
  }

  async rejectJobApplication(applicationId: number) {
    const response = await this.api.post(`/clients/applications/${applicationId}/reject/`);
    return response.data;
  }

  async rateServiceRequest(requestId: number, ratingData: {
    rating: number;
    review?: string;
  }) {
    const response = await this.api.post(`/v1/clients/requests/${requestId}/rate/`, ratingData);
    
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

  // ============== CONFIG API ==============
  
  // Get privacy policy
  async getPrivacyPolicy() {
    const response = await this.api.get('/config/privacy/');
    return response.data;
  }

  // Get terms of service
  async getTermsOfService() {
    const response = await this.api.get('/config/terms/');
    return response.data;
  }

  // Get contact info
  async getContactInfo() {
    const response = await this.api.get('/config/contact-info/');
    return response.data;
  }

  // Get FAQ
  async getFAQ() {
    const response = await this.api.get('/support/faq/');
    return response.data;
  }

  // ============== GDPR API ==============
  
  // Export user data (GDPR Article 20 - Right to Data Portability)
  async exportUserData() {
    const response = await this.api.get('/v1/gdpr/export/', {
      params: { format: 'json' }
    });
    return response.data;
  }

  // Get account deletion preview (shows what will be deleted)
  async getAccountDeletionPreview() {
    const response = await this.api.get('/v1/gdpr/delete/preview/');
    return response.data.preview || {};
  }

  // Delete account permanently (GDPR Article 17 - Right to Erasure)
  async deleteAccount() {
    const response = await this.api.post('/v1/gdpr/delete/', {
      confirm: true
    });
    return response.data;
  }

  // Anonymize account (soft delete - removes PII but keeps records)
  async anonymizeAccount() {
    const response = await this.api.post('/v1/gdpr/anonymize/', {
      confirm: true
    });
    return response.data;
  }

  // Get data retention policy information
  async getDataRetentionPolicy() {
    const response = await this.api.get('/v1/gdpr/retention/');
    return response.data;
  }

  // Get consent status
  async getConsentStatus() {
    const response = await this.api.get('/v1/gdpr/consent/');
    return response.data;
  }

  // Get privacy settings
  async getPrivacySettings() {
    const response = await this.api.get('/v1/accounts/privacy-settings/');
    return response.data;
  }

  // Update privacy settings
  async updatePrivacySettings(settings: any) {
    const response = await this.api.patch('/v1/accounts/privacy-settings/update/', settings);
    return response.data;
  }

  // Get data retention information
  async getDataRetention() {
    const response = await this.api.get('/v1/gdpr/retention/');
    return response.data;
  }

  // ============ PAYMENT METHODS ============
  // Get saved cards (for clients)
  async getPaymentMethods() {
    const response = await this.api.get('/v1/payment-methods/cards/');
    return response.data;
  }

  // Set default card
  async setDefaultCard(cardId: string) {
    const response = await this.api.post(`/v1/payment-methods/cards/${cardId}/set_default/`, {});
    return response.data;
  }

  // Remove saved card
  async removeCard(cardId: string) {
    const response = await this.api.delete(`/v1/payment-methods/cards/${cardId}/`);
    return response.data;
  }

  // Get bank accounts (for workers)
  async getBankAccounts() {
    const response = await this.api.get('/v1/payment-methods/bank-accounts/');
    return response.data;
  }

  // Set default bank account
  async setDefaultBankAccount(accountId: string) {
    const response = await this.api.post(`/v1/payment-methods/bank-accounts/${accountId}/set_default/`, {});
    return response.data;
  }

  // Remove bank account
  async removeBankAccount(accountId: string) {
    const response = await this.api.delete(`/v1/payment-methods/bank-accounts/${accountId}/`);
    return response.data;
  }

  // Get mobile money accounts (for workers)
  async getMobileMoneyAccounts() {
    const response = await this.api.get('/v1/payment-methods/mobile-money/');
    return response.data;
  }

  // Set default mobile money account
  async setDefaultMobileMoneyAccount(accountId: string) {
    const response = await this.api.post(`/v1/payment-methods/mobile-money/${accountId}/set_default/`, {});
    return response.data;
  }

  // Remove mobile money account
  async removeMobileMoneyAccount(accountId: string) {
    const response = await this.api.delete(`/v1/payment-methods/mobile-money/${accountId}/`);
    return response.data;
  }
}

// Export singleton instance
export default new ApiService();
