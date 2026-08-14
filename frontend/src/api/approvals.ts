import { apiClient } from "./client";
import type { ApprovalOut } from "./types";

export const approvalsApi = {
  listPending: () => apiClient.get<ApprovalOut[]>("/api/approvals").then((r) => r.data),
  decide: (approvalId: number, decision: "approved" | "rejected", note?: string) =>
    apiClient
      .post<ApprovalOut>(`/api/approvals/${approvalId}/decision`, { decision, note })
      .then((r) => r.data),
};
