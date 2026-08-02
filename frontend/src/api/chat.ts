import { apiClient } from "./client";
import type { AgentRunResult } from "./types";

export const chatApi = {
  send: (patientId: number, message: string) =>
    apiClient
      .post<AgentRunResult>(`/api/patients/${patientId}/chat`, { message })
      .then((r) => r.data),
};
