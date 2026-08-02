import { apiClient } from "./client";
import type { DrugInteractionWarning } from "./types";

export const interactionsApi = {
  list: (patientId: number) =>
    apiClient
      .get<DrugInteractionWarning[]>(`/api/patients/${patientId}/interactions`)
      .then((r) => r.data),
};
