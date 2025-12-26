// API Configuration
// Update these values based on your environment

import { Platform } from 'react-native';

const isDevelopment = __DEV__;

// For local development:
// - Physical device: Use your computer's local IP (find with `ipconfig` on Windows or `ifconfig` on Mac/Linux)
// - Android emulator: Use 10.0.2.2
// - iOS simulator: Use localhost or 127.0.0.1

export const API_CONFIG = {
  // Replace with your actual IP address when testing on physical device
  LOCAL_IP: '192.168.0.235',  // Updated to current IP
  LOCAL_PORT: '8000',
  
  // Production URL (update when deploying)
  PRODUCTION_URL: 'https://your-production-domain.com',
  
  // Auto-detect based on environment and platform
  get BASE_URL() {
    if (isDevelopment) {
      // Always use LOCAL_IP for all platforms (works for both emulator and physical devices)
      const host = this.LOCAL_IP;
      const url = `http://${host}:${this.LOCAL_PORT}`;
      console.log(`[API Config] Platform: ${Platform.OS}, Using BASE_URL: ${url}`);
      return url;
    }
    return this.PRODUCTION_URL;
  },
  
  get API_URL() {
    const apiUrl = `${this.BASE_URL}/api`;
    console.log(`[API Config] API_URL: ${apiUrl}`);
    return apiUrl;
  },
};

// How to find your local IP:
// Windows: Open CMD and run `ipconfig`, look for "IPv4 Address"
// Mac/Linux: Open Terminal and run `ifconfig` or `ip addr`, look for inet address
// Example: 192.168.1.100, 192.168.0.105, etc.

export default API_CONFIG;
