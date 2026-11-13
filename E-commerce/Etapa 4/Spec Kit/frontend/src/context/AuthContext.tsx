import React, { createContext, useContext, useState, ReactNode } from "react";
import { api } from "../services/api";

export interface AuthContextType {
  token: string | null;
  identifier: string | null;
  isAuthenticated: boolean;
  register: (identifier: string, password: string) => Promise<void>;
  signIn: (identifier: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [identifier, setIdentifier] = useState<string | null>(null);

  const register = async (id: string, password: string) => {
    // Call registration endpoint
    await api.registerUser(id, password);
    // Note: post-registration session status is left completely unspecified.
    // The account is created, but automatic sign-in is neither asserted nor denied.
  };

  const signIn = async (id: string, password: string) => {
    const res = await api.signInUser(id, password);
    setToken(res.session_token);
    setIdentifier(id);
  };

  const signOut = async () => {
    if (token) {
      try {
        await api.signOutUser(token);
      } catch (err) {
        console.error("Error during API signout:", err);
      }
    }
    // Visibly return to a non-authenticated state by clearing local memory.
    // Local shopping cart context is preserved (handled in components/app routing).
    setToken(null);
    setIdentifier(null);
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider
      value={{
        token,
        identifier,
        isAuthenticated,
        register,
        signIn,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
