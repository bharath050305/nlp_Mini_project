import { apiClient } from "./client";
import type { AnalyticsSummary, LabTrendPoint, ReminderAdherence } from "./types";

export const analyticsApi = {
  labTrends: (patientId: number) =>
    apiClient
      .get<LabTrendPoint[]>(`/api/patients/${patientId}/analytics/lab-trends`)
      .then((r) => r.data),
  adherence: (patientId: number, days = 30) =>
    apiClient
      .get<ReminderAdherence[]>(`/api/patients/${patientId}/analytics/adherence`, { params: { days } })
      .then((r) => r.data),
  summary: (patientId: number) =>
    apiClient
      .get<AnalyticsSummary>(`/api/patients/${patientId}/analytics/summary`)
      .then((r) => r.data),
};
