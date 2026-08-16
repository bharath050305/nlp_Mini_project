import { useState } from "react";
import type { ConsensusEvaluation, LabTrajectory } from "@/api/types";

interface ConsensusVisualizerProps {
  consensus?: ConsensusEvaluation | null;
  trajectories?: LabTrajectory[];
}

export default function ConsensusVisualizer({
  consensus,
  trajectories,
}: ConsensusVisualizerProps) {
  const [showDetails, setShowDetails] = useState(false);

  if (!consensus && (!trajectories || trajectories.length === 0)) {
    return null;
  }

  const primary = consensus?.primary_candidate;
  const status = consensus?.status;

  const statusConfig = {
    unanimous: {
      label: "Unanimous Consensus",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200",
      dot: "bg-emerald-500",
    },
    weighted_consensus: {
      label: "Weighted Evidence Consensus",
      bg: "bg-blue-50 text-blue-700 border-blue-200",
      dot: "bg-blue-500",
    },
    disputed: {
      label: "Disputed / Clinical Ambiguity",
      bg: "bg-amber-50 text-amber-800 border-amber-300",
      dot: "bg-amber-500",
    },
    safety_vetoed: {
      label: "Safety VETO Activated",
      bg: "bg-rose-50 text-rose-800 border-rose-300",
      dot: "bg-rose-500",
    },
    insufficient_evidence: {
      label: "Insufficient Evidence",
      bg: "bg-slate-100 text-slate-700 border-slate-200",
      dot: "bg-slate-400",
    },
  }[status || "weighted_consensus"];

  return (
    <div className="mt-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand-50 text-brand-600 font-semibold text-xs">
            MA
          </div>
          <div>
            <h4 className="text-xs font-semibold text-slate-800">
              Multi-Agent Consensus & Decision Support
            </h4>
            <p className="text-[11px] text-slate-400">
              Cross-deliberation across Clinical, Lab & Guideline Agents
            </p>
          </div>
        </div>
        {status && (
          <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium ${statusConfig.bg}`}
          >
            <span className={`h-1.5 w-1.5 rounded-full ${statusConfig.dot}`} />
            {statusConfig.label}
          </span>
        )}
      </div>

      {/* Safety Veto Alert */}
      {consensus?.safety_veto_triggered && (
        <div className="mt-3 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-800">
          <p className="font-semibold">⚠️ Hard Safety VETO Triggered</p>
          <p className="mt-0.5">{consensus.veto_reason}</p>
        </div>
      )}

      {/* Primary Candidate Card */}
      {primary && (
        <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50/70 p-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-slate-800">
                {primary.condition_name}
              </span>
              {primary.icd10_code && (
                <span className="rounded bg-slate-200/80 px-1.5 py-0.5 text-[10px] font-medium text-slate-600">
                  ICD-10: {primary.icd10_code}
                </span>
              )}
            </div>
            <span className="text-xs font-bold text-brand-600">
              {Math.round(primary.probability_score * 100)}% support
            </span>
          </div>

          {/* Score Bar */}
          <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
            <div
              className={`h-full transition-all duration-500 ${
                status === "disputed"
                  ? "bg-amber-500"
                  : status === "safety_vetoed"
                  ? "bg-rose-500"
                  : "bg-brand-600"
              }`}
              style={{ width: `${Math.round(primary.probability_score * 100)}%` }}
            />
          </div>

          {/* Secondary Differentials */}
          {consensus.secondary_candidates.length > 0 && (
            <div className="mt-3 space-y-1.5 border-t border-slate-200/60 pt-2">
              <p className="text-[11px] font-medium text-slate-400">
                Competing Differentials in Consensus:
              </p>
              {consensus.secondary_candidates.map((cand, idx) => (
                <div
                  key={idx}
                  className="flex items-center justify-between text-xs text-slate-600"
                >
                  <span>{cand.condition_name}</span>
                  <span className="font-medium text-slate-500">
                    {Math.round(cand.probability_score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Adversarial Critic Callout */}
      {consensus?.critic_notes && (
        <div className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/60 p-2.5 text-xs text-indigo-900">
          <p className="font-semibold text-indigo-800">
            🛡️ Adversarial Critic Review
          </p>
          <p className="mt-0.5 text-indigo-700">{consensus.critic_notes}</p>
        </div>
      )}

      {/* Lab Trajectory Indicators */}
      {trajectories && trajectories.length > 0 && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <p className="text-xs font-semibold text-slate-700">
            📈 Lab Trend Trajectories (Rate of Change)
          </p>
          <div className="mt-2 space-y-1.5">
            {trajectories.map((tr, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-1.5 text-xs"
              >
                <span className="font-medium text-slate-700">{tr.test_name}</span>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${
                      tr.trend_direction === "critical_drop" ||
                      tr.trend_direction === "critical_spike"
                        ? "bg-rose-100 text-rose-700"
                        : tr.trend_direction === "rising"
                        ? "bg-amber-100 text-amber-700"
                        : "bg-slate-200 text-slate-600"
                    }`}
                  >
                    {tr.trend_direction.replace("_", " ")}
                  </span>
                  <span className="text-[11px] text-slate-500 font-mono">
                    Δ {tr.slope_per_interval > 0 ? "+" : ""}
                    {tr.slope_per_interval}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Toggle Detailed Evidence Drawer */}
      {consensus && (
        <div className="mt-3 border-t border-slate-100 pt-2 text-right">
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="text-[11px] font-medium text-brand-600 hover:text-brand-700 hover:underline"
          >
            {showDetails ? "Hide Evidence Citations" : "View Grounded Citations & Recommended Tests"}
          </button>
        </div>
      )}

      {showDetails && consensus && (
        <div className="mt-2 space-y-2 rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
          {primary?.supporting_evidence && primary.supporting_evidence.length > 0 && (
            <div>
              <p className="font-semibold text-slate-700">Supporting Grounded Evidence:</p>
              <ul className="mt-1 list-inside list-disc space-y-1 text-[11px]">
                {primary.supporting_evidence.map((ev, idx) => (
                  <li key={idx} className="text-slate-600">
                    <span className="font-medium">[{ev.source_type}]</span> {ev.snippet}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {consensus.missing_information.length > 0 && (
            <div className="border-t border-slate-200/60 pt-2">
              <p className="font-semibold text-slate-700">
                Recommended Confirmatory Investigations:
              </p>
              <div className="mt-1 flex flex-wrap gap-1.5">
                {consensus.missing_information.map((test, idx) => (
                  <span
                    key={idx}
                    className="rounded-md border border-slate-200 bg-white px-2 py-0.5 text-[11px] text-slate-700 shadow-2xs"
                  >
                    {test}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
