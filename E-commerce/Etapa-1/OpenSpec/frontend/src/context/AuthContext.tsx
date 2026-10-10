import React, { createContext, useContext, useState, ReactNode } from 'react';

interface AuthContextType {
  sessionToken: string | null;
  accountIdentifier: string | null;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
  authError: string | null;
  login: (identifier: string, token: string) => void;
  logout: () => void;
  setIsAuthLoading: (loading: boolean) => void;
  setAuthError: (error: string | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [accountIdentifier, setAccountIdentifier] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  const login = (identifier: string, token: string) => {
    setSessionToken(token);
    setAccountIdentifier(identifier);
    setAuthError(null);
  };

  const logout = () => {
    setSessionToken(null);
    setAccountIdentifier(null);
    setAuthError(null);
  };

  const isAuthenticated = !!sessionToken;

  return (
    <AuthContext.Provider
      value={{
        sessionToken,
        accountIdentifier,
        isAuthenticated,
        isAuthLoading,
        authError,
        login,
        logout,
        setIsAuthLoading,
        setAuthError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
