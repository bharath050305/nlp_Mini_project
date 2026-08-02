import { apiClient } from "./client";
import type { NotificationOut } from "./types";

export interface ListNotificationsParams {
  unread_only?: boolean;
  limit?: number;
  offset?: number;
}

export const notificationsApi = {
  list: (params?: ListNotificationsParams) =>
    apiClient.get<NotificationOut[]>("/api/notifications", { params }).then((r) => r.data),
  markRead: (id: number) =>
    apiClient.patch<NotificationOut>(`/api/notifications/${id}/read`).then((r) => r.data),
  markAllRead: () =>
    apiClient
      .post<{ marked_read: number }>("/api/notifications/mark-all-read")
      .then((r) => r.data),
};
