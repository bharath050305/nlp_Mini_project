import { useState } from "react";
import type { ExecutionLogEntry } from "@/api/types";
import { AutonomyBadge, RiskBadge, StatusBadge } from "@/components/ui/Badge";

export default function ExecutionTimeline({ log }: { log: ExecutionLogEntry[] }) {
  const [open, setOpen] = useState(false);

  if (log.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-slate-100 bg-slate-50/70">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-slate-500 hover:text-slate-700"
      >
        <span>
          Agent execution trace ({log.length} step{log.length === 1 ? "" : "s"})
        </span>
        <span className={`transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>
      {open && (
        <ol className="flex flex-col gap-2 border-t border-slate-100 px-3 py-3">
          {log.map((entry, idx) => (
            <li
              key={idx}
              className="flex flex-col gap-1 rounded-md border border-slate-100 bg-white px-3 py-2"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-slate-700">{entry.agent_name}</span>
                <StatusBadge status={entry.status} />
                <AutonomyBadge autonomy={entry.autonomy} />
                <RiskBadge risk={entry.risk_tier} />
                {entry.duration_ms !== null && (
                  <span className="ml-auto text-xs text-slate-400">{entry.duration_ms} ms</span>
                )}
              </div>
              {entry.detail && <p className="text-xs text-slate-500">{entry.detail}</p>}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
