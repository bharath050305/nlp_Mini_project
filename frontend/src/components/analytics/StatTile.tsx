import type { ReactNode } from "react";
import Card, { CardBody } from "@/components/ui/Card";

export default function StatTile({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "warning" | "danger";
}) {
  const valueColor =
    tone === "danger" ? "text-rose-600" : tone === "warning" ? "text-amber-600" : "text-slate-800";
  return (
    <Card>
      <CardBody>
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className={`mt-1 text-2xl font-semibold ${valueColor}`}>{value}</p>
        {hint && <p className="mt-1 text-xs text-slate-400">{hint}</p>}
      </CardBody>
    </Card>
  );
}
