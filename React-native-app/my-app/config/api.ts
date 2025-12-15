// API Configuration
// Update these values based on your environment

const isDevelopment = __DEV__;

// For local development:
// - Physical device: Use your computer's local IP (find with `ipconfig` on Windows or `ifconfig` on Mac/Linux)
// - Android emulator: Use 10.0.2.2
// - iOS simulator: Use localhost or 127.0.0.1

export const API_CONFIG = {
  // Replace with your actual IP address when testing on physical device
  LOCAL_IP: '192.168.100.111',
  LOCAL_PORT: '8000',
  
  // Production URL (update when deploying)
  PRODUCTION_URL: 'https://your-production-domain.com',
  
  // Auto-detect based on environment
  get BASE_URL() {
    if (isDevelopment) {
      return `http://${this.LOCAL_IP}:${this.LOCAL_PORT}`;
    }
    return this.PRODUCTION_URL;
  },
  
  get API_URL() {
    return `${this.BASE_URL}/api`;
  },
};

// How to find your local IP:
// Windows: Open CMD and run `ipconfig`, look for "IPv4 Address"
// Mac/Linux: Open Terminal and run `ifconfig` or `ip addr`, look for inet address
// Example: 192.168.1.100, 192.168.0.105, etc.

export default API_CONFIG;
