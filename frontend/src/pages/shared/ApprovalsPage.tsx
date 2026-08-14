import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { approvalsApi } from "@/api/approvals";
import { getErrorMessage } from "@/api/client";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { formatDateTime } from "@/utils/format";
import type { ApprovalOut, ApprovalType } from "@/api/types";

const typeLabel: Record<ApprovalType, string> = {
  triage: "Risk triage",
  verification: "Unsupported answer",
  interaction: "Drug interaction",
};

/**
 * The human-in-the-loop worklist (v5): every item here was flagged by
 * the Supervisor agent (agents/supervisor_agent.py) after a chat turn —
 * a HIGH/CRITICAL triage result, an answer the Critic couldn't verify
 * against its evidence, or a major drug interaction. Approve/reject is
 * a real decision, stored with a reviewer, timestamp, and optional note.
 */
export default function ApprovalsPage() {
  const query = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: approvalsApi.listPending,
    refetchInterval: 30000,
  });

  if (query.isLoading) return <FullPageSpinner />;
  const approvals = query.data ?? [];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">Approvals</h1>
        <p className="text-sm text-slate-500">
          Chat responses flagged by the Supervisor agent for clinician review, across all of your assigned patients.
        </p>
      </div>

      {approvals.length === 0 ? (
        <EmptyState
          title="Nothing pending"
          description="Flagged items (high-risk triage, unsupported answers, major drug interactions) will show up here."
        />
      ) : (
        <div className="flex flex-col gap-4">
          {approvals.map((approval) => (
            <ApprovalItem key={approval.id} approval={approval} />
          ))}
        </div>
      )}
    </div>
  );
}

function ApprovalItem({ approval }: { approval: ApprovalOut }) {
  const queryClient = useQueryClient();
  const [note, setNote] = useState("");

  let detail: { user_request?: string; final_response?: string } = {};
  try {
    detail = JSON.parse(approval.detail_json);
  } catch {
    // detail_json should always be valid JSON (written by supervisor_agent.py);
    // fall back to showing just the summary if it's ever not.
  }

  const decide = useMutation({
    mutationFn: (decision: "approved" | "rejected") => approvalsApi.decide(approval.id, decision, note || undefined),
    onSuccess: (_, decision) => {
      toast.success(decision === "approved" ? "Approved." : "Rejected.");
      queryClient.invalidateQueries({ queryKey: ["approvals"] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <Card>
      <CardHeader className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Badge tone="warning">{typeLabel[approval.type]}</Badge>
          <span className="text-xs text-slate-400">{formatDateTime(approval.created_at)}</span>
        </div>
        <span className="text-xs text-slate-400">Patient #{approval.patient_id}</span>
      </CardHeader>
      <CardBody className="flex flex-col gap-3">
        <p className="text-sm font-medium text-slate-800">{approval.summary}</p>
        {detail.user_request && (
          <p className="text-xs text-slate-500">
            <span className="font-medium">Patient asked:</span> "{detail.user_request}"
          </p>
        )}
        {detail.final_response && (
          <p className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">{detail.final_response}</p>
        )}
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="Optional note (e.g. 'Discussed with patient by phone')"
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
        />
        <div className="flex gap-2">
          <Button
            variant="primary"
            size="sm"
            loading={decide.isPending && decide.variables === "approved"}
            disabled={decide.isPending}
            onClick={() => decide.mutate("approved")}
          >
            Approve
          </Button>
          <Button
            variant="danger"
            size="sm"
            loading={decide.isPending && decide.variables === "rejected"}
            disabled={decide.isPending}
            onClick={() => decide.mutate("rejected")}
          >
            Reject
          </Button>
        </div>
      </CardBody>
    </Card>
  );
}
