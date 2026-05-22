import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { TeacherProfile, whoami } from '../services/api';

interface AuthState {
  teacher: TeacherProfile | null;
  loading: boolean;
  signIn: (jwt: string) => Promise<void>;
  signOut: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthState | undefined>(undefined);

const TOKEN_KEY = 'token';

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [teacher, setTeacher] = useState<TeacherProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setTeacher(null);
      setLoading(false);
      return;
    }
    try {
      const me = await whoami();
      setTeacher(me);
    } catch {
      // Stored token is invalid or expired — wipe it.
      localStorage.removeItem(TOKEN_KEY);
      setTeacher(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const signIn = useCallback(async (jwt: string) => {
    localStorage.setItem(TOKEN_KEY, jwt);
    await refresh();
  }, [refresh]);

  const signOut = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setTeacher(null);
  }, []);

  return (
    <AuthContext.Provider value={{ teacher, loading, signIn, signOut, refresh }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthState => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
};
