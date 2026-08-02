import { apiClient } from "./client";
import type { AssignmentOut, AssignmentRole } from "./types";

export interface CreateAssignmentPayload {
  patient_id: number;
  staff_user_id: number;
  role_at_assignment: AssignmentRole;
}

export const assignmentsApi = {
  list: (patientId?: number) =>
    apiClient
      .get<AssignmentOut[]>("/api/assignments", {
        params: patientId ? { patient_id: patientId } : undefined,
      })
      .then((r) => r.data),
  create: (payload: CreateAssignmentPayload) =>
    apiClient.post<AssignmentOut>("/api/assignments", payload).then((r) => r.data),
  remove: (assignmentId: number) =>
    apiClient.delete(`/api/assignments/${assignmentId}`).then(() => undefined),
};
