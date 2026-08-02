import { apiClient } from "./client";
import type { PatientOut } from "./types";

export interface CreatePatientPayload {
  name: string;
  date_of_birth?: string | null;
  phone?: string | null;
}

export const patientsApi = {
  list: () => apiClient.get<PatientOut[]>("/api/patients").then((r) => r.data),
  me: () => apiClient.get<PatientOut>("/api/patients/me").then((r) => r.data),
  create: (payload: CreatePatientPayload) =>
    apiClient.post<PatientOut>("/api/patients", payload).then((r) => r.data),
  get: (patientId: number) =>
    apiClient.get<PatientOut>(`/api/patients/${patientId}`).then((r) => r.data),
};
