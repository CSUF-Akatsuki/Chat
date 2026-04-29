import axios, { type AxiosError } from "axios";
import apiClient from "./axiosInstance";
import type { FriendsProfile } from "../types/friends-types";
import store from "../store/store";
export interface ApiError {
  message?: string;
  detail?: string;
}
export async function getFriends() {
  try {
    const token = store.getState().auth.token;
    if (!token) {
      throw new Error("Authentication required. Please log in.");
    }
    const response = await apiClient.get<FriendsProfile[]>("/friends", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
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
    const response = await apiClient.get<FriendsProfile[]>(
      "/friends/suggestions",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
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
    const response = await apiClient.get<FriendsProfile[]>(
      "/friends/requests",
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
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
