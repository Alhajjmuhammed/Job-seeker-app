import React, { createContext, useState, useContext, useEffect } from 'react';
import { authService, User } from '../services/auth';
import { router } from 'expo-router';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadUser();
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
