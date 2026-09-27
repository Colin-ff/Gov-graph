import { createContext, useContext, useState } from "react";
import { login as apiLogin, registerUser as apiRegisterUser } from "../api/client";
import type { RegisterPayload, RegisterResult } from "../api/client";
import { clearAuth, getAuth, setAuth } from "./auth";
import type { AuthUser } from "./auth";

interface AuthContextValue {
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<RegisterResult>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  // Seed from localStorage so a refresh keeps the session.
  const [user, setUser] = useState<AuthUser | null>(getAuth);

  async function login(email: string, password: string): Promise<void> {
    const profile = await apiLogin(email, password);
    setAuth(profile);
    setUser(profile);
  }

  async function register(payload: RegisterPayload): Promise<RegisterResult> {
    const result = await apiRegisterUser(payload);
    if (result.kind === "authenticated") {
      setAuth(result.user);
      setUser(result.user);
    }
    return result;
  }

  function logout(): void {
    clearAuth();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === null) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
