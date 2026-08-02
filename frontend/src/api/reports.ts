import { apiClient } from "./client";
import type { ReportDetailOut, ReportOut, TimelineEvent } from "./types";

export const reportsApi = {
  list: (patientId: number) =>
    apiClient.get<ReportOut[]>(`/api/patients/${patientId}/reports`).then((r) => r.data),
  get: (patientId: number, reportId: number) =>
    apiClient
      .get<ReportDetailOut>(`/api/patients/${patientId}/reports/${reportId}`)
      .then((r) => r.data),
  upload: (patientId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<ReportOut>(`/api/patients/${patientId}/reports/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  timeline: (patientId: number) =>
    apiClient.get<TimelineEvent[]>(`/api/patients/${patientId}/timeline`).then((r) => r.data),
};
