import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '../api/client';

export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  created_at: string;
}

interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  quickLogin: (email: string) => Promise<void>;
  register: (email: string, password: string, fullName?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('aijob_token'));
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = async () => {
    try {
      const profile = await api.get<UserProfile>('/auth/me');
      setUser(profile);
    } catch {
      localStorage.removeItem('aijob_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const login = async (email: string, password: string) => {
    const res = await api.post<{ access_token: string; token_type: string }>('/auth/login', {
      email,
      password,
    });
    localStorage.setItem('aijob_token', res.access_token);
    setToken(res.access_token);
    await fetchCurrentUser();
  };

  const quickLogin = async (email: string) => {
    const res = await api.post<{ access_token: string; token_type: string }>('/auth/quick-login', {
      email,
    });
    localStorage.setItem('aijob_token', res.access_token);
    setToken(res.access_token);
    await fetchCurrentUser();
  };

  const register = async (email: string, password: string, fullName?: string) => {
    await api.post<UserProfile>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    // Auto-login after registration
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('aijob_token');
    setToken(null);
    setUser(null);
  };

  const refreshUser = async () => {
    if (token) {
      await fetchCurrentUser();
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        quickLogin,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
