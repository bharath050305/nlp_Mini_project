import type { TranscriptStatus as StatusType } from "@/api/types";
import Spinner from "@/components/ui/Spinner";
import { StatusBadge } from "@/components/ui/Badge";

const friendlyLabel: Record<StatusType, string> = {
  uploaded: "Queued for transcription...",
  transcribing: "Transcribing audio...",
  transcribed: "Transcription complete, preparing note...",
  structuring: "Drafting clinical note...",
  draft_ready: "Draft SOAP note ready for review",
  finalized: "Note finalized",
  failed: "Processing failed",
};

const inProgress: StatusType[] = ["uploaded", "transcribing", "transcribed", "structuring"];

export default function TranscriptStatus({
  status,
  errorDetail,
}: {
  status: StatusType;
  errorDetail?: string | null;
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-100 bg-slate-50/70 px-4 py-3">
      {inProgress.includes(status) && <Spinner className="h-4 w-4" />}
      <div>
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-slate-700">{friendlyLabel[status]}</p>
          <StatusBadge status={status} />
        </div>
        {status === "failed" && errorDetail && (
          <p className="mt-0.5 text-xs text-rose-500">{errorDetail}</p>
        )}
      </div>
    </div>
  );
}
