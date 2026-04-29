import axios, { type AxiosError } from "axios";
import apiClient from "./axiosInstance";
import type { FriendsProfile } from "../types/friends-types";
import store from "../store/store";
export interface ApiError {
  message?: string;
  detail?: string;
}

// Backend FriendsProfile uses `cognito_sub` for the user identifier; the
// frontend components consume `id`. Normalize at the API boundary so the
// components stay agnostic of the backend field rename.
type RawFriendsProfile = Omit<FriendsProfile, "id"> & { cognito_sub: string };
function normalize(p: RawFriendsProfile): FriendsProfile {
  return { ...p, id: p.cognito_sub };
}
export async function getFriends() {
  try {
    const token = store.getState().auth.token;
    if (!token) {
      throw new Error("Authentication required. Please log in.");
    }
    const response = await apiClient.get<RawFriendsProfile[]>("/friends", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data.map(normalize);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to fetch friends. Please try again."
      );
    }
  }
}

export async function getPeopleYouMayKnow() {
  try {
    const token = store.getState().auth.token;
    if (!token) {
      throw new Error("Authentication required. Please log in.");
    }
    const response = await apiClient.get<RawFriendsProfile[]>(
      "/friends/suggestions",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data.map(normalize);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to fetch friends. Please try again."
      );
    }
  }
}

export async function getFriendRequests() {
  try {
    const token = store.getState().auth.token;
    if (!token) {
      throw new Error("Authentication required. Please log in.");
    }
    const response = await apiClient.get<RawFriendsProfile[]>(
      "/friends/requests",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data.map(normalize);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to fetch friends. Please try again."
      );
    }
  }
}
