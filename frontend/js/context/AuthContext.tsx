import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { accountsAuthStatusRetrieve, AuthenticatedUser } from '@/js/api';
import { getAccessToken } from '@/js/utils';

interface AuthContextValue {
  user: AuthenticatedUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  refetch: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  refetch: () => {},
});

export const useAuth = (): AuthContextValue => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    const token = getAccessToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const response = await accountsAuthStatusRetrieve();
      setUser(response.data.user ?? null);
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      refetch: fetchUser,
    }),
    [user, isLoading, fetchUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
