import { apiClient } from "./client";
import type { AssignmentOut, AssignmentRole } from "./types";

export interface CreateAssignmentPayload {
  patient_id: number;
  staff_user_id: number;
  role_at_assignment: AssignmentRole;
}

export const assignmentsApi = {
  // The backend requires patient_id on GET /api/assignments (no "list all" mode),
  // so listing for a single patient is the only supported call shape.
  listForPatient: (patientId: number) =>
    apiClient
      .get<AssignmentOut[]>("/api/assignments", { params: { patient_id: patientId } })
      .then((r) => r.data),
  create: (payload: CreateAssignmentPayload) =>
    apiClient.post<AssignmentOut>("/api/assignments", payload).then((r) => r.data),
  remove: (assignmentId: number) =>
    apiClient.delete(`/api/assignments/${assignmentId}`).then(() => undefined),
};
