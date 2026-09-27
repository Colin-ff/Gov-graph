// Auth profile returned by POST /api/auth/login and persisted client-side.
// The token is replayed as the X-Token header (with X-User-Email) on protected
// calls — see the axios interceptor in src/api/client.ts.
export interface AuthUser {
  email: string;
  displayName: string;
  userRole: string;
  token: string;
}

const STORAGE_KEY = "govgraph_auth";

export function getAuth(): AuthUser | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

export function setAuth(user: AuthUser): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function clearAuth(): void {
  localStorage.removeItem(STORAGE_KEY);
}
