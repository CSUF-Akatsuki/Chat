export interface AuthState {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: User | null;
  token: string | null;
  error: string | null;
}
// Hydrate auth state from localStorage so a page refresh doesn't log the user
// out. We persist only the access token; user identity is decoded from the JWT
// claims when the slice initializes.
function hydrateInitialState(): AuthState {
  try {
    const token = localStorage.getItem("auth_token");
    if (!token) return base;
    const payload = token.split(".")[1];
    const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
    const claims = JSON.parse(atob(padded.replace(/-/g, "+").replace(/_/g, "/")));
    const exp = (claims.exp as number) * 1000;
    if (Number.isFinite(exp) && exp <= Date.now()) {
      localStorage.removeItem("auth_token");
      return base;
    }
    const sub = claims.sub as string;
    const username =
      (claims["cognito:username"] as string) ||
      (claims.username as string) ||
      sub;
    return {
      ...base,
      isAuthenticated: true,
      token,
      user: { id: sub, username, email: claims.email as string | undefined },
      isLoading: false,
    };
  } catch {
    return base;
  }
}
const base: AuthState = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
  token: null,
  error: null,
};
export const initialState: AuthState = hydrateInitialState();
export interface User {
  id: string; // Cognito sub (UUID)
  email?: string;
  username: string;
}
export interface UserDetail {
  id: string;
  email?: string;
  username: string;
  created_at?: Date;
}
export interface RegisterFormData {
  email: string;
  username: string;
  password: string;
}
export interface LoginFormData {
  username: string;
  password: string;
}
export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export interface ErrorResponse {
  detail: string;
}
