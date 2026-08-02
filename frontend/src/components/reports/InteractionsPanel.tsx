import type { DrugInteractionWarning } from "@/api/types";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";

export default function InteractionsPanel({
  warnings,
}: {
  warnings: DrugInteractionWarning[];
}) {
  if (warnings.length === 0) {
    return (
      <EmptyState
        title="No drug interactions detected"
        description="Interaction warnings will appear here based on the patient's current medicines."
      />
    );
  }

  return (
    <ul className="flex flex-col gap-2">
      {warnings.map((w, i) => (
        <li
          key={i}
          className="flex flex-col gap-1 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3"
        >
          <div className="flex items-center gap-2">
            <Badge tone={w.severity === "major" ? "danger" : "warning"}>{w.severity}</Badge>
            <span className="text-sm font-medium text-amber-900">
              {w.drug_a} + {w.drug_b}
            </span>
          </div>
          <p className="text-sm text-amber-800">{w.note}</p>
        </li>
      ))}
    </ul>
  );
}
