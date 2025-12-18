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
      // Add timeout to prevent infinite loading
      const timeoutPromise = new Promise((_, reject) => 
        setTimeout(() => reject(new Error('Timeout')), 3000)
      );
      
      const isAuth = await authService.isAuthenticated();
      if (isAuth) {
        const userData = await Promise.race([
          authService.getCurrentUser(),
          timeoutPromise
        ]) as User;
        setUser(userData);
      }
    } catch (error: any) {
      console.error('Error loading user:', error?.message || error);
      // If network error or timeout, clear auth and proceed to login
      if (error?.code === 'ECONNABORTED' || error?.message === 'Timeout' || error?.code === 'ERR_NETWORK') {
        await authService.logout();
      }
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
        router.replace('/(worker)/dashboard');
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
        router.replace('/(worker)/dashboard');
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
