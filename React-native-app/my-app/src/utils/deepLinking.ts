/**
 * Deep linking configuration for Worker Connect mobile app.
 * 
 * This module provides utilities for handling deep links and universal links.
 */

import * as Linking from 'expo-linking';
import { router } from 'expo-router';

/**
 * Deep link URL scheme
 */
export const DEEP_LINK_SCHEME = 'workerconnect://';

/**
 * Universal link domain
 */
export const UNIVERSAL_LINK_DOMAIN = 'https://workerconnect.com';

/**
 * Deep link routes mapping
 */
export const DEEP_LINK_ROUTES = {
  // Job routes
  'job/:id': '/jobs/[id]',
  'jobs': '/jobs',
  'job/:id/apply': '/jobs/[id]/apply',
  
  // Worker routes
  'worker/:id': '/workers/[id]',
  'workers': '/workers',
  'worker/:id/portfolio': '/workers/[id]/portfolio',
  
  // Profile routes
  'profile': '/profile',
  'profile/edit': '/profile/edit',
  'portfolio': '/profile/portfolio',
  
  // Auth routes
  'login': '/auth/login',
  'register': '/auth/register',
  'reset-password': '/auth/reset-password',
  'verify-email': '/auth/verify-email',
  
  // Dashboard routes
  'dashboard': '/dashboard',
  'notifications': '/notifications',
  'messages': '/messages',
  'message/:id': '/messages/[id]',
  
  // Invoice routes
  'invoice/:id': '/invoices/[id]',
  'invoices': '/invoices',
  
  // Review routes
  'review/:id': '/reviews/[id]',
  'leave-review/:jobId': '/jobs/[jobId]/review',
  
  // Settings routes
  'settings': '/settings',
  'settings/notifications': '/settings/notifications',
  'settings/privacy': '/settings/privacy',
  'settings/payments': '/settings/payments',
};

/**
 * Generate a deep link URL
 */
export function createDeepLink(route: string, params?: Record<string, string>): string {
  let url = `${DEEP_LINK_SCHEME}${route}`;
  
  if (params) {
    const queryString = new URLSearchParams(params).toString();
    url += `?${queryString}`;
  }
  
  return url;
}

/**
 * Generate a universal link URL
 */
export function createUniversalLink(route: string, params?: Record<string, string>): string {
  let url = `${UNIVERSAL_LINK_DOMAIN}/app/${route}`;
  
  if (params) {
    const queryString = new URLSearchParams(params).toString();
    url += `?${queryString}`;
  }
  
  return url;
}

/**
 * Parse a deep link URL and extract route and params
 */
export function parseDeepLink(url: string): { route: string; params: Record<string, string> } | null {
  try {
    const parsed = Linking.parse(url);
    
    return {
      route: parsed.path || '',
      params: (parsed.queryParams as Record<string, string>) || {},
    };
  } catch (error) {
    console.error('Failed to parse deep link:', error);
    return null;
  }
}

/**
 * Handle incoming deep link
 */
export function handleDeepLink(url: string): void {
  const parsed = parseDeepLink(url);
  
  if (!parsed) {
    console.warn('Could not parse deep link:', url);
    return;
  }
  
  const { route, params } = parsed;
  
  // Find matching route
  let appRoute = findAppRoute(route, params);
  
  if (appRoute) {
    // Navigate to the route
    router.push(appRoute as any);
  } else {
    console.warn('No matching route found for:', route);
    // Navigate to home or show error
    router.push('/');
  }
}

/**
 * Find the app route for a deep link path
 */
function findAppRoute(path: string, params: Record<string, string>): string | null {
  // Check direct route mapping
  for (const [pattern, appRoute] of Object.entries(DEEP_LINK_ROUTES)) {
    const match = matchRoute(path, pattern);
    if (match) {
      // Replace route params
      let finalRoute = appRoute;
      for (const [key, value] of Object.entries(match)) {
        finalRoute = finalRoute.replace(`[${key}]`, value);
      }
      
      // Add query params
      if (Object.keys(params).length > 0) {
        const queryString = new URLSearchParams(params).toString();
        finalRoute += `?${queryString}`;
      }
      
      return finalRoute;
    }
  }
  
  return null;
}

/**
 * Match a path against a route pattern
 */
function matchRoute(path: string, pattern: string): Record<string, string> | null {
  const pathParts = path.split('/').filter(Boolean);
  const patternParts = pattern.split('/').filter(Boolean);
  
  if (pathParts.length !== patternParts.length) {
    return null;
  }
  
  const params: Record<string, string> = {};
  
  for (let i = 0; i < patternParts.length; i++) {
    const patternPart = patternParts[i];
    const pathPart = pathParts[i];
    
    if (patternPart.startsWith(':')) {
      // This is a parameter
      const paramName = patternPart.slice(1);
      params[paramName] = pathPart;
    } else if (patternPart !== pathPart) {
      // No match
      return null;
    }
  }
  
  return params;
}

/**
 * Set up deep link listener
 */
export function setupDeepLinkListener(): () => void {
  // Handle initial URL (app opened via deep link)
  Linking.getInitialURL().then((url) => {
    if (url) {
      handleDeepLink(url);
    }
  });
  
  // Handle URLs while app is running
  const subscription = Linking.addEventListener('url', (event) => {
    handleDeepLink(event.url);
  });
  
  // Return cleanup function
  return () => {
    subscription.remove();
  };
}

/**
 * Share deep link utilities
 */
export const DeepLinkUtils = {
  // Generate shareable job link
  jobLink: (jobId: string | number) => createUniversalLink(`job/${jobId}`),
  
  // Generate shareable worker profile link
  workerLink: (workerId: string | number) => createUniversalLink(`worker/${workerId}`),
  
  // Generate shareable portfolio link
  portfolioLink: (workerId: string | number) => createUniversalLink(`worker/${workerId}/portfolio`),
  
  // Generate invoice link
  invoiceLink: (invoiceId: string | number) => createUniversalLink(`invoice/${invoiceId}`),
  
  // Generate review link
  reviewLink: (reviewId: string | number) => createUniversalLink(`review/${reviewId}`),
};

export default {
  DEEP_LINK_SCHEME,
  UNIVERSAL_LINK_DOMAIN,
  DEEP_LINK_ROUTES,
  createDeepLink,
  createUniversalLink,
  parseDeepLink,
  handleDeepLink,
  setupDeepLinkListener,
  DeepLinkUtils,
};
