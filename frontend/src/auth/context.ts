import { createContext } from "react";
import type { Role } from "../api/types";

export type AuthContextValue = {
  isAuthenticated: boolean;
  role: Role | null;
  isAdmin: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
