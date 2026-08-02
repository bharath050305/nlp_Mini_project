import { apiClient } from "./client";
import type { SoapNoteOut, TranscriptOut } from "./types";

export type UpdateSoapPayload = Partial<{
  subjective: string;
  objective: string;
  assessment: string;
  plan: string;
}>;

export const transcriptsApi = {
  upload: (patientId: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient
      .post<TranscriptOut>(`/api/patients/${patientId}/transcripts/upload`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
  listForPatient: (patientId: number) =>
    apiClient
      .get<TranscriptOut[]>(`/api/patients/${patientId}/transcripts`)
      .then((r) => r.data),
  get: (transcriptId: number) =>
    apiClient.get<TranscriptOut>(`/api/transcripts/${transcriptId}`).then((r) => r.data),
  getSoap: (transcriptId: number) =>
    apiClient.get<SoapNoteOut>(`/api/transcripts/${transcriptId}/soap`).then((r) => r.data),
  updateSoap: (transcriptId: number, payload: UpdateSoapPayload) =>
    apiClient
      .patch<SoapNoteOut>(`/api/transcripts/${transcriptId}/soap`, payload)
      .then((r) => r.data),
  finalize: (transcriptId: number) =>
    apiClient
      .post<SoapNoteOut>(`/api/transcripts/${transcriptId}/finalize`)
      .then((r) => r.data),
};
