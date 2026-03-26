import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { authApi, campaignBriefApi } from '@/lib/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // Check if user is authenticated on mount
  const checkAuth = useCallback(async () => {
    try {
      const userData = await authApi.getMe();
      setUser(userData);
      // Link any anonymous briefs to this user
      await campaignBriefApi.linkToUser();
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
      setInitialCheckDone(true);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // Login with Google
  const loginWithGoogle = (redirectPath = '/dashboard') => {
    // Replace REACT_APP_AUTH_URL with your OAuth provider URL
    const redirectUrl = window.location.origin + redirectPath;
    window.location.href = `${process.env.REACT_APP_AUTH_URL}/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  // Exchange session ID for token
  const exchangeSession = async (sessionId) => {
    try {
      const userData = await authApi.exchangeSession(sessionId);
      setUser(userData);
      // Link any anonymous briefs to this user
      await campaignBriefApi.linkToUser();
      return userData;
    } catch (error) {
      console.error('Session exchange failed:', error);
      throw error;
    }
  };

  // Logout
  const logout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      setUser(null);
    }
  };

  const value = {
    user,
    loading,
    initialCheckDone,
    isAuthenticated: !!user,
    loginWithGoogle,
    exchangeSession,
    logout,
    checkAuth,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
