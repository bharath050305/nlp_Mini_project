import { apiClient } from "./client";
import type { AgentCapabilityOut } from "./types";

export const registryApi = {
  list: () => apiClient.get<AgentCapabilityOut[]>("/api/admin/agents").then((r) => r.data),
};
