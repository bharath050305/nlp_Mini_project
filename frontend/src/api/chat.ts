import { apiClient } from "./client";
import type { AgentRunResult } from "./types";

export const chatApi = {
  send: (patientId: number, message: string) =>
    apiClient
      .post<AgentRunResult>(`/api/patients/${patientId}/chat`, { message })
      .then((r) => r.data),
  sendVoice: (patientId: number, audioBlob: Blob) => {
    const form = new FormData();
    form.append("file", audioBlob, "voice-message.webm");
    return apiClient
      .post<AgentRunResult>(`/api/patients/${patientId}/chat/voice`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};
