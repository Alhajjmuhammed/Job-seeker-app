import i18next from 'i18next';
import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService, User } from '../services/auth';
import apiService from '../services/api';
import { router } from 'expo-router';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadUser();
  }, []);

  // Session ended on the server: go back to the login screen instead of
  // leaving the user on screens where every request now fails.
  useEffect(() => {
    let handled = false;
    apiService.setOnAuthExpired(() => {
      if (handled) return;
      handled = true;
      setUser(null);
      router.replace('/(auth)/login');
      setTimeout(() => { handled = false; }, 2000);
    });
  }, []);

  const loadUser = async () => {
    try {
      const isAuth = await authService.isAuthenticated();
      if (isAuth) {
        try {
          const userData = await authService.getCurrentUser();
          setUser(userData);
        } catch (userError: any) {
          console.log('Could not load user data:', userError?.message || 'Unknown error');
          // Clear invalid auth state
          await authService.logout();
          setUser(null);
        }
      }
    } catch (error: any) {
      console.log('Auth check failed:', error?.message || 'Unknown error');
      // Clear auth state on error
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const response = await authService.login(email, password);
      // The app has screens for workers and clients only. Agents and admins
      // work on the website - sign them out again with a clear message
      // instead of leaving them on the login screen with no feedback.
      const kind = response.user?.userType;
      if (kind !== 'worker' && kind !== 'client') {
        await authService.logout().catch(() => {});
        throw new Error(i18next.t('auth.useWebsite'));
      }
      setUser(response.user);
      
      // Navigate based on user type
      if (response.user.userType === 'worker') {
        // Check if profile is complete (for first-time login)
        if (!response.user.isProfileComplete) {
          router.replace('/(worker)/profile-setup');
        } else {
          router.replace('/(worker)/dashboard');
        }
      } else if (response.user.userType === 'client') {
        router.replace('/(client)/dashboard');
      }
    } catch (error) {
      throw error;
    }
  };

  const register = async (userData: any) => {
    try {
      const response = await authService.register(userData);
      setUser(response.user);
      
      // Navigate based on user type
      if (response.user.userType === 'worker') {
        // Check if profile is complete
        if (!response.user.isProfileComplete) {
          router.replace('/(worker)/profile-setup');
        } else {
          router.replace('/(worker)/dashboard');
        }
      } else if (response.user.userType === 'client') {
        router.replace('/(client)/dashboard');
      }
    } catch (error) {
      throw error;
    }
  };

  // Re-read the user (e.g. after the worker changes their type in the
  // profile, so Browse Jobs shows or hides without restarting the app).
  const refreshUser = async () => {
    const fresh = await authService.getCurrentUser();
    if (fresh) setUser(fresh);
  };

  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      router.replace('/(auth)/login');
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
