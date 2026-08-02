import { apiClient } from "./client";
import type { UserOut } from "./types";

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiClient.post<UserOut>("/api/auth/register", payload).then((r) => r.data),
  login: (payload: LoginPayload) =>
    apiClient.post<UserOut>("/api/auth/login", payload).then((r) => r.data),
  logout: () => apiClient.post("/api/auth/logout").then(() => undefined),
  me: () => apiClient.get<UserOut>("/api/auth/me").then((r) => r.data),
};
