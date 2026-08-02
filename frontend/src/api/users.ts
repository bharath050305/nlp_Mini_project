import { apiClient } from "./client";
import type { Role, UserOut } from "./types";

export interface CreateUserPayload {
  email: string;
  password: string;
  full_name: string;
  role: Role;
}

export const usersApi = {
  list: (role?: Role) =>
    apiClient
      .get<UserOut[]>("/api/users", { params: role ? { role } : undefined })
      .then((r) => r.data),
  create: (payload: CreateUserPayload) =>
    apiClient.post<UserOut>("/api/users", payload).then((r) => r.data),
};
