import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, readToken, setUnauthorizedHandler, writeToken } from "../api/client";
import type { LoginResponse, Role } from "../api/types";
import { AuthContext, type AuthContextValue } from "./context";

function decodeRole(token: string): Role | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role === "admin" || payload.role === "viewer" ? payload.role : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setToken] = useState<string | null>(() => readToken());

  const logout = useCallback(() => {
    writeToken(null);
    setToken(null);
    qc.clear();
  }, [qc]);

  useEffect(() => {
    setUnauthorizedHandler(() => setToken(null));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { data } = await apiFetch<LoginResponse>("/auth/login", { form: { username, password } });
    writeToken(data.access_token);
    setToken(data.access_token);
  }, []);

  const value = useMemo<AuthContextValue>(() => {
    const role = token ? decodeRole(token) : null;
    return {
      isAuthenticated: Boolean(token),
      role,
      isAdmin: role === "admin",
      login,
      logout,
    };
  }, [token, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
