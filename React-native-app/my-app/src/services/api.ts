/**
 * API Service Layer for Worker Connect Mobile App.
 * 
 * Provides a centralized, type-safe interface for all API calls.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';

// Configuration
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://api.workerconnect.com';
const API_VERSION = 'v1';
const API_TIMEOUT = 30000; // 30 seconds

// Token storage key
const AUTH_TOKEN_KEY = '@WorkerConnect:authToken';
const REFRESH_TOKEN_KEY = '@WorkerConnect:refreshToken';

/**
 * API Error class
 */
export class APIError extends Error {
  status: number;
  data: any;
  
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Request configuration type
 */
interface RequestConfig {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: any;
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean>;
  requiresAuth?: boolean;
  timeout?: number;
}

/**
 * Pagination parameters
 */
interface PaginationParams {
  page?: number;
  limit?: number;
  cursor?: string;
}

/**
 * API Response wrapper
 */
interface APIResponse<T> {
  data: T;
  status: number;
  headers: Headers;
}

/**
 * Core API service
 */
class APIService {
  private baseUrl: string;
  private version: string;
  private authToken: string | null = null;
  private refreshToken: string | null = null;
  
  constructor() {
    this.baseUrl = API_BASE_URL;
    this.version = API_VERSION;
    this.loadTokens();
  }
  
  /**
   * Load auth tokens from storage
   */
  private async loadTokens(): Promise<void> {
    try {
      this.authToken = await AsyncStorage.getItem(AUTH_TOKEN_KEY);
      this.refreshToken = await AsyncStorage.getItem(REFRESH_TOKEN_KEY);
    } catch (error) {
      console.error('Failed to load auth tokens:', error);
    }
  }
  
  /**
   * Save auth tokens to storage
   */
  async saveTokens(authToken: string, refreshToken?: string): Promise<void> {
    try {
      this.authToken = authToken;
      await AsyncStorage.setItem(AUTH_TOKEN_KEY, authToken);
      
      if (refreshToken) {
        this.refreshToken = refreshToken;
        await AsyncStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      }
    } catch (error) {
      console.error('Failed to save auth tokens:', error);
    }
  }
  
  /**
   * Clear auth tokens
   */
  async clearTokens(): Promise<void> {
    try {
      this.authToken = null;
      this.refreshToken = null;
      await AsyncStorage.multiRemove([AUTH_TOKEN_KEY, REFRESH_TOKEN_KEY]);
    } catch (error) {
      console.error('Failed to clear auth tokens:', error);
    }
  }
  
  /**
   * Check if user is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.authToken;
  }
  
  /**
   * Build URL with query parameters
   */
  private buildUrl(endpoint: string, params?: Record<string, any>): string {
    let url = `${this.baseUrl}/api/${this.version}${endpoint}`;
    
    if (params && Object.keys(params).length > 0) {
      const searchParams = new URLSearchParams();
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value));
        }
      });
      url += `?${searchParams.toString()}`;
    }
    
    return url;
  }
  
  /**
   * Make API request
   */
  async request<T>(endpoint: string, config: RequestConfig = {}): Promise<APIResponse<T>> {
    const {
      method = 'GET',
      body,
      headers = {},
      params,
      requiresAuth = true,
      timeout = API_TIMEOUT,
    } = config;
    
    // Build headers
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'X-API-Version': this.version,
      ...headers,
    };
    
    // Add auth header if needed
    if (requiresAuth && this.authToken) {
      requestHeaders['Authorization'] = `Token ${this.authToken}`;
    }
    
    // Build URL
    const url = this.buildUrl(endpoint, params);
    
    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    
    try {
      const response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      
      clearTimeout(timeoutId);
      
      // Parse response
      let data: T;
      const contentType = response.headers.get('content-type');
      if (contentType?.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text() as unknown as T;
      }
      
      // Handle errors
      if (!response.ok) {
        // Handle 401 - try to refresh token
        if (response.status === 401 && this.refreshToken) {
          const refreshed = await this.tryRefreshToken();
          if (refreshed) {
            // Retry request with new token
            return this.request(endpoint, config);
          }
        }
        
        throw new APIError(
          (data as any)?.message || (data as any)?.error || 'Request failed',
          response.status,
          data
        );
      }
      
      return {
        data,
        status: response.status,
        headers: response.headers,
      };
    } catch (error) {
      clearTimeout(timeoutId);
      
      if (error instanceof APIError) {
        throw error;
      }
      
      if ((error as Error).name === 'AbortError') {
        throw new APIError('Request timeout', 408);
      }
      
      throw new APIError((error as Error).message, 0);
    }
  }
  
  /**
   * Try to refresh auth token
   */
  private async tryRefreshToken(): Promise<boolean> {
    if (!this.refreshToken) return false;
    
    try {
      const response = await fetch(`${this.baseUrl}/api/${this.version}/auth/refresh/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      
      if (response.ok) {
        const data = await response.json();
        await this.saveTokens(data.token, data.refresh_token);
        return true;
      }
    } catch (error) {
      console.error('Token refresh failed:', error);
    }
    
    await this.clearTokens();
    return false;
  }
  
  // Convenience methods
  
  get<T>(endpoint: string, params?: Record<string, any>): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'GET', params });
  }
  
  post<T>(endpoint: string, body?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'POST', body });
  }
  
  put<T>(endpoint: string, body?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'PUT', body });
  }
  
  patch<T>(endpoint: string, body?: any): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'PATCH', body });
  }
  
  delete<T>(endpoint: string): Promise<APIResponse<T>> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

// Create singleton instance
const api = new APIService();

/**
 * Auth API
 */
export const AuthAPI = {
  login: (email: string, password: string) =>
    api.post<{ token: string; user: any }>('/auth/login/', { email, password }),
  
  register: (data: { email: string; password: string; user_type: string; first_name?: string; last_name?: string }) =>
    api.post<{ token: string; user: any }>('/auth/register/', data),
  
  logout: () => api.post('/auth/logout/'),
  
  getProfile: () => api.get<any>('/auth/profile/'),
  
  updateProfile: (data: any) => api.patch<any>('/auth/profile/', data),
  
  changePassword: (currentPassword: string, newPassword: string) =>
    api.post('/auth/change-password/', { current_password: currentPassword, new_password: newPassword }),
  
  requestPasswordReset: (email: string) =>
    api.post('/auth/password-reset/', { email }),
  
  saveTokens: (token: string, refreshToken?: string) =>
    api.saveTokens(token, refreshToken),
  
  clearTokens: () => api.clearTokens(),
  
  isAuthenticated: () => api.isAuthenticated(),
};

/**
 * Jobs API
 */
export const JobsAPI = {
  list: (params?: PaginationParams & { status?: string; category?: number }) =>
    api.get<{ jobs: any[]; count: number }>('/jobs/', params),
  
  get: (id: number) => api.get<any>(`/jobs/${id}/`),
  
  create: (data: any) => api.post<any>('/jobs/create/', data),
  
  update: (id: number, data: any) => api.patch<any>(`/jobs/${id}/`, data),
  
  delete: (id: number) => api.delete(`/jobs/${id}/`),
  
  apply: (jobId: number, data: { cover_letter?: string; proposed_rate?: number }) =>
    api.post<any>(`/jobs/${jobId}/apply/`, data),
  
  getApplications: (jobId: number) =>
    api.get<any[]>(`/jobs/${jobId}/applications/`),
  
  assignWorker: (jobId: number, workerId: number) =>
    api.post<any>(`/jobs/${jobId}/assign/`, { worker_id: workerId }),
  
  startJob: (jobId: number) => api.post<any>(`/jobs/${jobId}/start/`),
  
  completeJob: (jobId: number) => api.post<any>(`/jobs/${jobId}/complete/`),
  
  search: (query: string, filters?: any) =>
    api.get<any>('/search/jobs/', { q: query, ...filters }),
  
  getRecommendations: () => api.get<any[]>('/jobs/recommendations/'),
  
  getSaved: () => api.get<any[]>('/jobs/saved/'),
  
  saveJob: (jobId: number) => api.post(`/jobs/${jobId}/save/`),
  
  unsaveJob: (jobId: number) => api.delete(`/jobs/${jobId}/save/`),
};

/**
 * Workers API
 */
export const WorkersAPI = {
  list: (params?: PaginationParams & { category?: number; rating?: number }) =>
    api.get<{ workers: any[]; count: number }>('/workers/', params),
  
  get: (id: number) => api.get<any>(`/workers/${id}/`),
  
  getProfile: () => api.get<any>('/workers/profile/'),
  
  updateProfile: (data: any) => api.patch<any>('/workers/profile/', data),
  
  getAvailability: () => api.get<any>('/workers/availability/'),
  
  updateAvailability: (data: any) => api.put<any>('/workers/availability/', data),
  
  getEarnings: (params?: { period?: string }) =>
    api.get<any>('/earnings/', params),
  
  getPortfolio: (workerId: number) =>
    api.get<any[]>(`/portfolio/worker/${workerId}/`),
  
  addPortfolioItem: (data: any) => api.post<any>('/portfolio/add/', data),
  
  updatePortfolioItem: (id: number, data: any) =>
    api.put<any>(`/portfolio/${id}/update/`, data),
  
  deletePortfolioItem: (id: number) => api.delete(`/portfolio/${id}/delete/`),
  
  getBadges: (workerId: number) => api.get<any[]>(`/badges/worker/${workerId}/`),
  
  getMyBadges: () => api.get<any[]>('/badges/my/'),
  
  applyForBadge: (badgeType: string) =>
    api.post<any>('/badges/apply/', { badge_type: badgeType }),
};

/**
 * Clients API
 */
export const ClientsAPI = {
  getProfile: () => api.get<any>('/client/profile/'),
  
  updateProfile: (data: any) => api.patch<any>('/client/profile/', data),
  
  getPostedJobs: (params?: PaginationParams) =>
    api.get<any>('/client/jobs/', params),
  
  getDashboard: () => api.get<any>('/client/dashboard/'),
};

/**
 * Reviews API
 */
export const ReviewsAPI = {
  create: (data: { job_id: number; reviewee_id: number; overall_rating: number; comment?: string }) =>
    api.post<any>('/reviews/', data),
  
  get: (id: number) => api.get<any>(`/reviews/${id}/`),
  
  getForUser: (userId: number) => api.get<any[]>(`/reviews/user/${userId}/`),
  
  getMyReviews: () => api.get<any[]>('/reviews/my/'),
  
  respond: (reviewId: number, response: string) =>
    api.post<any>(`/reviews/${reviewId}/respond/`, { response }),
  
  flag: (reviewId: number, reason: string) =>
    api.post<any>(`/reviews/${reviewId}/flag/`, { reason }),
};

/**
 * Invoices API
 */
export const InvoicesAPI = {
  list: (params?: { status?: string }) =>
    api.get<any>('/invoices/', params),
  
  get: (id: number) => api.get<any>(`/invoices/${id}/`),
  
  create: (data: any) => api.post<any>('/invoices/create/', data),
  
  send: (id: number) => api.post<any>(`/invoices/${id}/send/`),
  
  markPaid: (id: number) => api.post<any>(`/invoices/${id}/paid/`),
  
  cancel: (id: number) => api.post<any>(`/invoices/${id}/cancel/`),
  
  getSummary: () => api.get<any>('/invoices/summary/'),
};

/**
 * Categories API
 */
export const CategoriesAPI = {
  list: (params?: { with_counts?: boolean }) =>
    api.get<{ categories: any[] }>('/categories/', params),
  
  get: (id: number) => api.get<any>(`/categories/${id}/`),
  
  getPopular: (limit?: number) =>
    api.get<any>('/categories/popular/', { limit }),
};

/**
 * Activity API
 */
export const ActivityAPI = {
  getFeed: (params?: { limit?: number; types?: string; unread?: boolean }) =>
    api.get<any>('/activity/feed/', params),
  
  markRead: (id: number) => api.post(`/activity/${id}/read/`),
  
  markAllRead: () => api.post('/activity/mark-all-read/'),
  
  getUnreadCount: () => api.get<{ unread_count: number }>('/activity/unread-count/'),
};

/**
 * Messaging API
 */
export const MessagingAPI = {
  getConversations: () => api.get<any[]>('/messaging/conversations/'),
  
  getMessages: (conversationId: number) =>
    api.get<any[]>(`/messaging/conversations/${conversationId}/messages/`),
  
  sendMessage: (conversationId: number, content: string) =>
    api.post<any>(`/messaging/conversations/${conversationId}/messages/`, { content }),
  
  createConversation: (recipientId: number, initialMessage?: string) =>
    api.post<any>('/messaging/conversations/', {
      recipient_id: recipientId,
      message: initialMessage,
    }),
};

/**
 * Notifications API
 */
export const NotificationsAPI = {
  getPreferences: () => api.get<any>('/notifications/preferences/'),
  
  updatePreferences: (data: any) =>
    api.put<any>('/notifications/preferences/', data),
};

/**
 * Config API
 */
export const ConfigAPI = {
  getAppConfig: () => api.get<any>('/config/app/', { requiresAuth: false }),
  
  getFeatureFlags: () => api.get<any>('/config/features/'),
};

// Export API instance for custom requests
export default api;
