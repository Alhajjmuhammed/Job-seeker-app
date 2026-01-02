/**
 * Deep Link Navigation Handler for Worker Connect Mobile App
 * 
 * Handles navigation from deep links and push notifications.
 */

import { Linking, Platform } from 'react-native';
import { router } from 'expo-router';

// Note: expo-notifications not available in Expo Go SDK 53+
console.log('[DeepLinkHandler] Notifications disabled in Expo Go');

// Deep link scheme configuration
export const DEEP_LINK_CONFIG = {
  prefixes: [
    'workerconnect://',
    'https://workerconnect.com',
    'https://app.workerconnect.com',
  ],
  // URL to screen mapping
  screens: {
    // Auth screens
    'login': '/(auth)/login',
    'register': '/(auth)/register',
    'reset-password': '/(auth)/reset-password',
    
    // Main screens
    'home': '/(tabs)',
    'jobs': '/(tabs)/jobs',
    'workers': '/(tabs)/workers',
    'profile': '/(tabs)/profile',
    'messages': '/(tabs)/messages',
    
    // Job screens
    'job/:id': '/jobs/[id]',
    'jobs/:id': '/jobs/[id]',
    'job/:id/apply': '/jobs/[id]/apply',
    'jobs/:id/applications': '/jobs/[id]/applications',
    
    // Worker screens
    'worker/:id': '/workers/[id]',
    'workers/:id': '/workers/[id]',
    
    // Application screens
    'application/:id': '/applications/[id]',
    'applications/:id': '/applications/[id]',
    'my-applications': '/applications',
    
    // Invoice screens
    'invoice/:id': '/invoices/[id]',
    'invoices/:id': '/invoices/[id]',
    'invoices': '/invoices',
    
    // Notification screens
    'notifications': '/notifications',
    
    // Settings
    'settings': '/settings',
    'settings/profile': '/settings/profile',
    'settings/notifications': '/settings/notifications',
    'settings/payment': '/settings/payment',
  },
};

// Parse parameters from URL path
function parsePathParams(pattern: string, path: string): Record<string, string> | null {
  const patternParts = pattern.split('/');
  const pathParts = path.split('/');
  
  if (patternParts.length !== pathParts.length) {
    return null;
  }
  
  const params: Record<string, string> = {};
  
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = pathParts[i];
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  
  return params;
}

// Parse query parameters from URL
function parseQueryParams(url: string): Record<string, string> {
  const params: Record<string, string> = {};
  const queryString = url.split('?')[1];
  
  if (!queryString) return params;
  
  queryString.split('&').forEach(param => {
    const [key, value] = param.split('=');
    if (key && value) {
      params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
  });
  
  return params;
}

// Parse deep link URL
export function parseDeepLink(url: string): {
  screen: string;
  params: Record<string, string>;
  query: Record<string, string>;
} | null {
  try {
    // Remove prefix
    let path = url;
    for (const prefix of DEEP_LINK_CONFIG.prefixes) {
      if (url.startsWith(prefix)) {
        path = url.slice(prefix.length);
        break;
      }
    }
    
    // Remove leading slash
    path = path.replace(/^\//, '');
    
    // Separate path and query
    const [pathPart, queryPart] = path.split('?');
    const query = parseQueryParams(url);
    
    // Find matching screen
    for (const [pattern, screen] of Object.entries(DEEP_LINK_CONFIG.screens)) {
      const params = parsePathParams(pattern, pathPart);
      if (params !== null) {
        return { screen, params, query };
      }
    }
    
    // Default to home if no match
    return { screen: '/(tabs)', params: {}, query };
  } catch (error) {
    console.error('Error parsing deep link:', error);
    return null;
  }
}

// Navigate to deep link
export async function navigateToDeepLink(url: string): Promise<boolean> {
  const parsed = parseDeepLink(url);
  
  if (!parsed) {
    console.warn('Could not parse deep link:', url);
    return false;
  }
  
  try {
    const { screen, params, query } = parsed;
    
    // Build route with params
    let route = screen;
    for (const [key, value] of Object.entries(params)) {
      route = route.replace(`[${key}]`, value);
    }
    
    // Add query params if present
    if (Object.keys(query).length > 0) {
      const queryString = new URLSearchParams(query).toString();
      route = `${route}?${queryString}`;
    }
    
    // Navigate using expo-router
    router.push(route as any);
    
    return true;
  } catch (error) {
    console.error('Error navigating to deep link:', error);
    return false;
  }
}

// Handle notification response (when user taps notification)
export function handleNotificationResponse(
  response: any
): void {
  const data = response.notification.request.content.data;
  
  if (data?.deepLink) {
    navigateToDeepLink(data.deepLink as string);
    return;
  }
  
  // Handle specific notification types
  const type = data?.type as string;
  const id = data?.id as string;
  
  switch (type) {
    case 'job_application':
    case 'application_received':
      if (id) router.push(`/applications/${id}` as any);
      break;
      
    case 'application_accepted':
    case 'application_rejected':
      if (id) router.push(`/applications/${id}` as any);
      break;
      
    case 'new_job':
    case 'job_assigned':
    case 'job_completed':
      if (id) router.push(`/jobs/${id}` as any);
      break;
      
    case 'new_message':
      if (id) router.push(`/messages/${id}` as any);
      else router.push('/messages' as any);
      break;
      
    case 'new_review':
      router.push('/profile/reviews' as any);
      break;
      
    case 'invoice_received':
    case 'payment_received':
      if (id) router.push(`/invoices/${id}` as any);
      break;
      
    case 'badge_earned':
      router.push('/profile/badges' as any);
      break;
      
    default:
      // Navigate to notifications screen for unknown types
      router.push('/notifications' as any);
  }
}

// Initialize deep link handling
export function initializeDeepLinking(
  onDeepLink?: (url: string) => void
): () => void {
  // Handle initial URL (app opened via deep link)
  Linking.getInitialURL().then(url => {
    if (url) {
      navigateToDeepLink(url);
      onDeepLink?.(url);
    }
  });
  
  // Listen for deep links while app is open
  const linkingSubscription = Linking.addEventListener('url', ({ url }) => {
    navigateToDeepLink(url);
    onDeepLink?.(url);
  });
  
  // Notification taps not available in Expo Go SDK 53+
  
  // Return cleanup function
  return () => {
    linkingSubscription.remove();
  };
}

// Generate deep link URL for sharing
export function generateDeepLink(
  screen: string,
  params?: Record<string, string | number>,
  useUniversalLink = true
): string {
  const prefix = useUniversalLink 
    ? 'https://workerconnect.com' 
    : 'workerconnect://';
  
  let path = screen;
  
  if (params) {
    // Replace path parameters
    for (const [key, value] of Object.entries(params)) {
      path = path.replace(`:${key}`, String(value));
    }
  }
  
  return `${prefix}/${path}`;
}

// Common deep link generators
export const DeepLinks = {
  job: (id: string | number) => generateDeepLink('job/:id', { id }),
  worker: (id: string | number) => generateDeepLink('worker/:id', { id }),
  application: (id: string | number) => generateDeepLink('application/:id', { id }),
  invoice: (id: string | number) => generateDeepLink('invoice/:id', { id }),
  message: (conversationId: string | number) => generateDeepLink('messages/:id', { id: conversationId }),
  profile: () => generateDeepLink('profile'),
  settings: () => generateDeepLink('settings'),
};

export default {
  DEEP_LINK_CONFIG,
  parseDeepLink,
  navigateToDeepLink,
  handleNotificationResponse,
  initializeDeepLinking,
  generateDeepLink,
  DeepLinks,
};
