import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';

interface OfflineAction {
  id: string;
  endpoint: string;
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  data?: any;
  timestamp: number;
  retries: number;
}

class OfflineService {
  private syncQueue: OfflineAction[] = [];
  private readonly QUEUE_KEY = '@offline_queue';
  private readonly CACHE_PREFIX = '@cache_';
  private readonly MAX_RETRIES = 3;
  private readonly CACHE_EXPIRY = 24 * 60 * 60 * 1000; // 24 hours
  private isOnline: boolean = true;

  constructor() {
    this.initNetworkMonitoring();
    this.loadQueue();
  }

  private initNetworkMonitoring() {
    NetInfo.addEventListener(state => {
      const wasOffline = !this.isOnline;
      this.isOnline = state.isConnected || false;
      
      // When coming back online, process queued actions
      if (wasOffline && this.isOnline) {
        console.log('Back online, processing queued actions');
        this.processSyncQueue();
      }
    });
  }

  async isConnected(): Promise<boolean> {
    const state = await NetInfo.fetch();
    return state.isConnected || false;
  }

  // Cache management
  async cacheData(key: string, data: any, expiryMs?: number): Promise<void> {
    try {
      const cacheItem = {
        data,
        timestamp: Date.now(),
        expiry: expiryMs || this.CACHE_EXPIRY,
      };
      await AsyncStorage.setItem(
        `${this.CACHE_PREFIX}${key}`,
        JSON.stringify(cacheItem)
      );
    } catch (error) {
      console.error('Error caching data:', error);
    }
  }

  async getCachedData<T>(key: string): Promise<T | null> {
    try {
      const cached = await AsyncStorage.getItem(`${this.CACHE_PREFIX}${key}`);
      if (!cached) return null;

      const cacheItem = JSON.parse(cached);
      const now = Date.now();

      // Check if cache is expired
      if (now - cacheItem.timestamp > cacheItem.expiry) {
        await this.clearCache(key);
        return null;
      }

      return cacheItem.data as T;
    } catch (error) {
      console.error('Error getting cached data:', error);
      return null;
    }
  }

  async clearCache(key?: string): Promise<void> {
    try {
      if (key) {
        await AsyncStorage.removeItem(`${this.CACHE_PREFIX}${key}`);
      } else {
        // Clear all cached data
        const keys = await AsyncStorage.getAllKeys();
        const cacheKeys = keys.filter(k => k.startsWith(this.CACHE_PREFIX));
        await AsyncStorage.multiRemove(cacheKeys);
      }
    } catch (error) {
      console.error('Error clearing cache:', error);
    }
  }

  // Offline queue management
  async queueAction(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
    data?: any
  ): Promise<void> {
    const action: OfflineAction = {
      id: `${Date.now()}_${Math.random()}`,
      endpoint,
      method,
      data,
      timestamp: Date.now(),
      retries: 0,
    };

    this.syncQueue.push(action);
    await this.saveQueue();
    
    console.log('Action queued for offline sync:', action);
  }

  private async loadQueue(): Promise<void> {
    try {
      const queueData = await AsyncStorage.getItem(this.QUEUE_KEY);
      if (queueData) {
        this.syncQueue = JSON.parse(queueData);
      }
    } catch (error) {
      console.error('Error loading offline queue:', error);
    }
  }

  private async saveQueue(): Promise<void> {
    try {
      await AsyncStorage.setItem(this.QUEUE_KEY, JSON.stringify(this.syncQueue));
    } catch (error) {
      console.error('Error saving offline queue:', error);
    }
  }

  async processSyncQueue(): Promise<void> {
    if (this.syncQueue.length === 0) return;
    if (!await this.isConnected()) return;

    console.log(`Processing ${this.syncQueue.length} queued actions`);

    const failedActions: OfflineAction[] = [];

    for (const action of this.syncQueue) {
      try {
        // TODO: Import and use your API service to execute the action
        // await apiService.request(action.endpoint, action.method, action.data);
        console.log('Successfully synced action:', action.id);
      } catch (error) {
        console.error('Error syncing action:', action.id, error);
        
        action.retries++;
        if (action.retries < this.MAX_RETRIES) {
          failedActions.push(action);
        } else {
          console.log('Max retries reached, discarding action:', action.id);
        }
      }
    }

    this.syncQueue = failedActions;
    await this.saveQueue();
  }

  async clearQueue(): Promise<void> {
    this.syncQueue = [];
    await AsyncStorage.removeItem(this.QUEUE_KEY);
  }

  getQueueSize(): number {
    return this.syncQueue.length;
  }

  getOnlineStatus(): boolean {
    return this.isOnline;
  }

  // Utility method to wrap API calls with offline support
  async withOfflineSupport<T>(
    key: string,
    apiFn: () => Promise<T>,
    options?: {
      cache?: boolean;
      cacheExpiry?: number;
      fallbackValue?: T;
    }
  ): Promise<T> {
    const isOnline = await this.isConnected();

    // Try to fetch from cache first if offline
    if (!isOnline && options?.cache) {
      const cached = await this.getCachedData<T>(key);
      if (cached) {
        console.log('Returning cached data for:', key);
        return cached;
      }
      
      if (options.fallbackValue !== undefined) {
        return options.fallbackValue;
      }
      
      throw new Error('No internet connection and no cached data available');
    }

    // Try to fetch from API
    try {
      const data = await apiFn();
      
      // Cache the result if requested
      if (options?.cache) {
        await this.cacheData(key, data, options.cacheExpiry);
      }
      
      return data;
    } catch (error) {
      // If API call fails, try cache as fallback
      if (options?.cache) {
        const cached = await this.getCachedData<T>(key);
        if (cached) {
          console.log('API call failed, returning cached data for:', key);
          return cached;
        }
      }
      
      if (options?.fallbackValue !== undefined) {
        return options.fallbackValue;
      }
      
      throw error;
    }
  }
}

export default new OfflineService();
