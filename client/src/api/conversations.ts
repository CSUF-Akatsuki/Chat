import axios, { type AxiosError } from "axios";
import apiClient from "./axiosInstance";
import type { Message, Conversations } from "../types/conversations-types";
import store from "../store/store";

export interface ApiError {
  message?: string;
  detail?: string;
}

function authHeader() {
  const token = store.getState().auth.token;
  if (!token) throw new Error("Authentication required. Please log in.");
  return { Authorization: `Bearer ${token}` };
}

export async function getAllConversations() {
  try {
    const response = await apiClient.get<Conversations>("/conversations", {
      headers: authHeader(),
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to fetch conversations. Please try again."
      );
    }
  }
}

export async function retrieverChatHistory(other_user_id: string) {
  try {
    const response = await apiClient.get<Message[]>(
      `/messages/${other_user_id}?limit=50&offset=0`,
      { headers: authHeader() }
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const axiosError = error as AxiosError<ApiError>;
      throw new Error(
        axiosError.response?.data?.message ||
          axiosError.response?.data?.detail ||
          "Failed to fetch conversations. Please try again."
      );
    }
  }
}
