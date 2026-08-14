import { apiClient } from "./client";
import type { DigitalTwin } from "./types";

export const digitalTwinApi = {
  get: (patientId: number) =>
    apiClient.get<DigitalTwin>(`/api/patients/${patientId}/digital-twin`).then((r) => r.data),
};
