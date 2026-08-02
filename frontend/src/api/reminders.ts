import { apiClient } from "./client";
import type { ReminderOut, ReminderSlotInput, ScheduleType } from "./types";

export interface CreateReminderPayload {
  medicine_name: string;
  dosage?: string | null;
  schedule_type: ScheduleType;
  quantity_total?: number | null;
  quantity_per_dose?: number | null;
  low_stock_threshold?: number | null;
  slots: ReminderSlotInput[];
}

export type UpdateReminderPayload = Partial<{
  medicine_name: string;
  dosage: string | null;
  schedule_type: ScheduleType;
  quantity_total: number | null;
  quantity_remaining: number | null;
  quantity_per_dose: number | null;
  low_stock_threshold: number | null;
  active: boolean;
}>;

export interface MarkDosePayload {
  slot_id?: number;
  status: "taken" | "skipped";
}

export interface MarkDoseResult {
  quantity_remaining: number | null;
  refill_alert_sent: boolean;
}

export const remindersApi = {
  list: (patientId: number) =>
    apiClient.get<ReminderOut[]>(`/api/patients/${patientId}/reminders`).then((r) => r.data),
  create: (patientId: number, payload: CreateReminderPayload) =>
    apiClient
      .post<ReminderOut>(`/api/patients/${patientId}/reminders`, payload)
      .then((r) => r.data),
  update: (patientId: number, reminderId: number, payload: UpdateReminderPayload) =>
    apiClient
      .patch<ReminderOut>(`/api/patients/${patientId}/reminders/${reminderId}`, payload)
      .then((r) => r.data),
  remove: (patientId: number, reminderId: number) =>
    apiClient
      .delete(`/api/patients/${patientId}/reminders/${reminderId}`)
      .then(() => undefined),
  markDose: (patientId: number, reminderId: number, payload: MarkDosePayload) =>
    apiClient
      .post<MarkDoseResult>(`/api/patients/${patientId}/reminders/${reminderId}/mark-dose`, payload)
      .then((r) => r.data),
};
