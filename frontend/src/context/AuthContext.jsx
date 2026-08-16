import React, { createContext, useContext, useState, useEffect } from 'react';

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
  const [token, setToken] = useState(localStorage.getItem('auth_token'));
  const [loading, setLoading] = useState(true);
  const [selectedCompany, setSelectedCompany] = useState(
    JSON.parse(localStorage.getItem('fp_company') || 'null')
  );

  const API_URL = import.meta.env.VITE_API_URL || '';

  useEffect(() => {
    if (token) {
      verifyToken();
    } else {
      setLoading(false);
    }
  }, []);

  // Ensure selectedCompany is valid for the current user
  useEffect(() => {
    if (user && user.companies) {
      if (selectedCompany) {
        const stillValid = user.companies.find(c => c.id === selectedCompany.id);
        if (!stillValid) {
          setSelectedCompany(user.companies[0] || null);
          localStorage.setItem('fp_company', JSON.stringify(user.companies[0] || null));
        }
      } else if (user.companies.length > 0) {
        setSelectedCompany(user.companies[0]);
        localStorage.setItem('fp_company', JSON.stringify(user.companies[0]));
      }
    }
  }, [user]);

  const verifyToken = async () => {
    try {
      const response = await fetch(API_URL + '/auth/verify', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data.user);
      } else {
        logout();
      }
    } catch (error) {
      console.error('Token verification failed:', error);
      logout();
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await fetch(API_URL + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Login failed');
    }
    setToken(data.access_token);
    setUser(data.user);
    localStorage.setItem('auth_token', data.access_token);
    // Auto-select first company
    if (data.user.companies && data.user.companies.length > 0) {
      setSelectedCompany(data.user.companies[0]);
      localStorage.setItem('fp_company', JSON.stringify(data.user.companies[0]));
    }
    return data;
  };

  const register = async (email, password, fullName) => {
    const response = await fetch(API_URL + '/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name: fullName })
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }
    return data;
  };

  const logout = () => {
    if (token) {
      fetch(API_URL + '/auth/logout', {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      }).catch(() => {});
    }
    setToken(null);
    setUser(null);
    setSelectedCompany(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('fp_company');
  };

  const selectCompany = (company) => {
    setSelectedCompany(company);
    localStorage.setItem('fp_company', JSON.stringify(company));
  };

  const isAdmin = () => user?.role === 'admin';

  const refreshUser = async () => {
    if (!token) return;
    try {
      const response = await fetch(API_URL + '/auth/me', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data);
      }
    } catch (e) {
      console.error('Failed to refresh user:', e);
    }
  };

  const value = {
    user, token, loading, login, register, logout, isAdmin,
    selectedCompany, selectCompany, refreshUser,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
