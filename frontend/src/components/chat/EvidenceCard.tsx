import type { AgentRunResult } from "@/api/types";
import Badge from "@/components/ui/Badge";

export default function EvidenceCard({ result }: { result: AgentRunResult }) {
  const { summary, qa_results, interaction_warnings, reminders, timeline } = result;

  const hasContent =
    summary ||
    qa_results.length > 0 ||
    interaction_warnings.length > 0 ||
    reminders.length > 0 ||
    timeline.length > 0;

  if (!hasContent) return null;

  return (
    <div className="mt-3 flex flex-col gap-3">
      {summary && (
        <div className="rounded-lg border border-brand-100 bg-brand-50/50 p-3">
          <div className="mb-1 flex items-center gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-brand-700">
              Report summary
            </p>
            <Badge tone="brand">{summary.confidence}</Badge>
          </div>
          <p className="text-sm text-slate-700">{summary.patient_summary}</p>
          {summary.key_findings.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-slate-500">Key findings</p>
              <ul className="ml-4 list-disc text-sm text-slate-600">
                {summary.key_findings.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.abnormal_values.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-slate-500">Abnormal values</p>
              <ul className="ml-4 list-disc text-sm text-rose-600">
                {summary.abnormal_values.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.recommendations.length > 0 && (
            <div className="mt-2">
              <p className="text-xs font-medium text-slate-500">Recommendations</p>
              <ul className="ml-4 list-disc text-sm text-slate-600">
                {summary.recommendations.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          )}
          {summary.evidence.length > 0 && (
            <div className="mt-2 flex flex-col gap-1.5">
              <p className="text-xs font-medium text-slate-500">Evidence</p>
              {summary.evidence.map((e, i) => (
                <div key={i} className="rounded-md bg-white px-2 py-1.5 text-xs text-slate-600">
                  <span className="font-medium text-slate-700">{e.claim}</span>
                  <span className="block text-slate-500">{e.evidence}</span>
                  {e.reference_range && (
                    <span className="block text-slate-400">Reference: {e.reference_range}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {qa_results.length > 0 && (
        <div className="flex flex-col gap-2">
          {qa_results.map((qa, i) => (
            <div key={i} className="rounded-lg border border-slate-100 bg-white p-3">
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium text-slate-700">{qa.question}</p>
                <Badge
                  tone={
                    qa.confidence === "high"
                      ? "success"
                      : qa.confidence === "medium"
                        ? "info"
                        : "warning"
                  }
                >
                  {qa.confidence}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-slate-600">{qa.answer}</p>
            </div>
          ))}
        </div>
      )}

      {interaction_warnings.length > 0 && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Drug interaction warnings
          </p>
          <ul className="flex flex-col gap-1">
            {interaction_warnings.map((w, i) => (
              <li key={i} className="text-sm text-amber-800">
                <Badge tone={w.severity === "major" ? "danger" : "warning"} className="mr-2">
                  {w.severity}
                </Badge>
                {w.drug_a} + {w.drug_b}: {w.note}
              </li>
            ))}
          </ul>
        </div>
      )}

      {reminders.length > 0 && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-emerald-700">
            Reminders created / updated
          </p>
          <ul className="flex flex-col gap-1 text-sm text-emerald-800">
            {reminders.map((r) => (
              <li key={r.id}>
                {r.medicine_name} {r.dosage ? `(${r.dosage})` : ""} — {r.schedule_type}
              </li>
            ))}
          </ul>
        </div>
      )}

      {timeline.length > 0 && (
        <div className="rounded-lg border border-slate-100 bg-white p-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Timeline events referenced
          </p>
          <ul className="flex flex-col gap-1 text-sm text-slate-600">
            {timeline.map((t, i) => (
              <li key={i}>
                {t.report_filename} — {t.diseases.join(", ") || "no diseases noted"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
