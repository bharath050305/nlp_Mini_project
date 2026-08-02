import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReminderAdherence } from "@/api/types";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";

function adherenceColor(pct: number): string {
  if (pct >= 80) return "#059669"; // emerald-600
  if (pct >= 50) return "#d97706"; // amber-600
  return "#e11d48"; // rose-600
}

function AdherenceTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d: ReminderAdherence = payload[0].payload;
  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-slate-700">{d.medicine_name}</p>
      <p className="text-slate-500">
        {d.taken} taken &middot; {d.missed} missed &middot; {d.skipped} skipped
      </p>
      <p className="mt-1 font-medium" style={{ color: adherenceColor(d.adherence_pct) }}>
        {d.adherence_pct}% adherence
      </p>
    </div>
  );
}

export default function AdherenceChart({ data }: { data: ReminderAdherence[] }) {
  if (data.length === 0) {
    return (
      <EmptyState
        title="No reminder adherence data yet"
        description="Once doses are marked taken (or missed), adherence per medicine shows up here."
      />
    );
  }

  return (
    <Card>
      <CardHeader>
        <span className="text-sm font-semibold text-slate-700">Medicine adherence (last 30 days)</span>
      </CardHeader>
      <CardBody>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="medicine_name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }} width={36} />
              <Tooltip content={<AdherenceTooltip />} />
              <Bar dataKey="adherence_pct" radius={[6, 6, 0, 0]}>
                {data.map((d) => (
                  <Cell key={d.reminder_id} fill={adherenceColor(d.adherence_pct)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </CardBody>
    </Card>
  );
}
