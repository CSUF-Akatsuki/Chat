import {
  createAsyncThunk,
  createSlice,
  type PayloadAction,
} from "@reduxjs/toolkit";
import { AxiosError } from "axios";
import apiClient from "../../api/axiosInstance";
import { initialState } from "../../types/auth-types";
import type {
  User,
  RegisterFormData,
  LoginFormData,
  AuthResponse,
} from "../../types/auth-types";

function decodeJwt(token: string): Record<string, unknown> {
  const payload = token.split(".")[1];
  const padded = payload + "=".repeat((4 - (payload.length % 4)) % 4);
  const json = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(json);
}

function userFromToken(token: string): User {
  const claims = decodeJwt(token);
  const sub = claims.sub as string;
  const username =
    (claims["cognito:username"] as string) ||
    (claims.username as string) ||
    sub;
  const email = claims.email as string | undefined;
  return { id: sub, username, email };
}

export const RegisterUser = createAsyncThunk<
  { message: string },
  RegisterFormData,
  { rejectValue: string }
>("auth/register", async (formData, thunkAPI) => {
  try {
    const response = await apiClient.post("/auth/register", formData);
    return response.data;
  } catch (error) {
    const axiosError = error as AxiosError<{ detail: string }>;
    return thunkAPI.rejectWithValue(
      axiosError.response?.data?.detail || "Registration failed"
    );
  }
});

export const loginUser = createAsyncThunk<
  { user: User; token: string },
  LoginFormData,
  { rejectValue: string }
>("auth/login", async (formData, thunkAPI) => {
  try {
    const response = await apiClient.post<AuthResponse>("/auth/login", formData);
    const token = response.data.access_token;
    return { user: userFromToken(token), token };
  } catch (error) {
    const axiosError = error as AxiosError<{ detail: string }>;
    return thunkAPI.rejectWithValue(
      axiosError.response?.data?.detail || "Login failed"
    );
  }
});

export const refreshAccessToken = createAsyncThunk<
  string,
  void,
  { rejectValue: string }
>("auth/refresh", async (_, thunkAPI) => {
  try {
    const response = await apiClient.post<AuthResponse>(
      "/auth/refresh",
      {},
      { withCredentials: true }
    );
    return response.data.access_token;
  } catch (error) {
    const axiosError = error as AxiosError<{ detail: string }>;
    return thunkAPI.rejectWithValue(
      axiosError.response?.data?.detail || "Token refresh failed"
    );
  }
});

export const checkAuth = createAsyncThunk<User, void, { rejectValue: string }>(
  "auth/checkAuth",
  async (_, thunkAPI) => {
    const state = thunkAPI.getState() as { auth: typeof initialState };
    const token = state.auth.token;
    if (!token) {
      return thunkAPI.rejectWithValue("No token");
    }
    try {
      return userFromToken(token);
    } catch {
      return thunkAPI.rejectWithValue("Invalid token");
    }
  }
);

export const logoutUser = createAsyncThunk("auth/logout", async (_, thunkAPI) => {
  const state = thunkAPI.getState() as { auth: typeof initialState };
  const token = state.auth.token;
  try {
    await apiClient.post(
      "/auth/logout",
      {},
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    );
  } catch {
    // logout is best-effort; clear local state regardless
  }
});

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    setUser: (state, action: PayloadAction<User | null>) => {
      state.user = action.payload;
      state.isAuthenticated = !!action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
    resetAuth: (state) => {
      state.isAuthenticated = false;
      state.user = null;
      state.token = null;
      state.error = null;
      state.isLoading = false;
      try { localStorage.removeItem("auth_token"); } catch {}
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(RegisterUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(RegisterUser.fulfilled, (state) => {
        state.isLoading = false;
        state.error = null;
      })
      .addCase(RegisterUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Registration failed";
        state.isAuthenticated = false;
        state.user = null;
      })

      .addCase(loginUser.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload.user;
        state.token = action.payload.token;
        state.error = null;
        try { localStorage.setItem("auth_token", action.payload.token); } catch {}
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.payload || "Login failed";
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
      })

      .addCase(refreshAccessToken.fulfilled, (state, action) => {
        state.token = action.payload;
        state.user = userFromToken(action.payload);
        state.isAuthenticated = true;
      })
      .addCase(refreshAccessToken.rejected, (state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
      })

      .addCase(checkAuth.pending, (state) => {
        state.isLoading = true;
      })
      .addCase(checkAuth.fulfilled, (state, action) => {
        state.isLoading = false;
        state.isAuthenticated = true;
        state.user = action.payload;
        state.error = null;
      })
      .addCase(checkAuth.rejected, (state) => {
        state.isLoading = false;
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.error = null;
      })

      .addCase(logoutUser.fulfilled, (state) => {
        state.isAuthenticated = false;
        state.user = null;
        state.token = null;
        state.error = null;
        state.isLoading = false;
        try { localStorage.removeItem("auth_token"); } catch {}
      });
  },
});

export const { setUser, clearError, resetAuth } = authSlice.actions;
export default authSlice.reducer;
