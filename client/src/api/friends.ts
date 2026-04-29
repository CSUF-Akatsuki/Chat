import axios, { type AxiosError } from "axios";
import apiClient from "./axiosInstance";
import type { ApiError } from "./fetchFriends";
import store from "../store/store";

function authHeader() {
  const token = store.getState().auth.token;
  if (!token) throw new Error("Authentication required. Please log in");
  return { Authorization: `Bearer ${token}` };
}

export async function sendFriendRequest(friendId: string) {
  try {
    const response = await apiClient.post(
      "/friends/request",
      { cognito_sub: friendId },
      { headers: authHeader() }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to send Friend Request. Please try again."
      );
    }
  }
}

export async function acceptFriendRequest(friendId: string) {
  try {
    await apiClient.post(
      `/friends/accept/${friendId}`,
      {},
      { headers: authHeader() }
    );
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to accept Friend Request Please try again."
      );
    }
  }
}

export async function rejectFriendRequest(friendId: string) {
  try {
    await apiClient.post(
      `/friends/reject/${friendId}`,
      {},
      { headers: authHeader() }
    );
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to reject Friend Request Please try again."
      );
    }
  }
}
