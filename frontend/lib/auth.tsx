"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { api, tokenStore } from "./api";
import type { AdminProfile } from "./types";

interface AuthState {
  profile: AdminProfile | null;
  loading: boolean;
  can: (perm: string) => boolean;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<AdminProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (!tokenStore.access) {
      setLoading(false);
      router.replace("/login");
      return;
    }
    api
      .get<AdminProfile>("/auth/me")
      .then(setProfile)
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  const logout = () => {
    const refresh = tokenStore.refresh;
    if (refresh) api.post("/auth/logout", { refreshToken: refresh }).catch(() => {});
    tokenStore.clear();
    router.replace("/login");
  };

  const can = (perm: string) => profile?.permissions.includes(perm) ?? false;

  return (
    <AuthContext.Provider value={{ profile, loading, can, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
