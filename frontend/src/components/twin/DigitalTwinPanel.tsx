import { useQuery } from "@tanstack/react-query";
import { digitalTwinApi } from "@/api/digitalTwin";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody, CardHeader } from "@/components/ui/Card";
import Badge, { TriageBadge } from "@/components/ui/Badge";
import StatTile from "@/components/analytics/StatTile";
import { formatDateTime } from "@/utils/format";

/**
 * Consolidated read-model view (v5) — every field here comes from
 * GET /api/patients/{id}/digital-twin, which itself just aggregates data
 * from agents already used elsewhere (entities, lab analysis, triage,
 * adherence). This panel doesn't compute anything new, it just presents
 * it in one place instead of five separate tabs.
 */
export default function DigitalTwinPanel({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["digital-twin", patientId],
    queryFn: () => digitalTwinApi.get(patientId),
  });

  if (query.isLoading) return <FullPageSpinner />;
  if (!query.data) {
    return <p className="text-sm text-slate-400">Digital Twin data isn't available for this patient yet.</p>;
  }
  const twin = query.data;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Total reports" value={twin.total_reports} />
        <StatTile
          label="Active reminders"
          value={twin.active_reminders}
        />
        <StatTile
          label="Adherence (30d)"
          value={`${twin.overall_adherence_pct}%`}
          tone={twin.overall_adherence_pct < 70 ? "warning" : "default"}
        />
        <StatTile
          label="Missed doses (7d)"
          value={twin.doses_missed_this_week}
          tone={twin.doses_missed_this_week > 0 ? "warning" : "default"}
        />
      </div>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">Current risk level</h3>
          <TriageBadge level={twin.triage_level} />
        </CardHeader>
        <CardBody>
          {twin.triage_reasons.length === 0 ? (
            <p className="text-sm text-slate-400">No abnormal findings or critical symptoms detected.</p>
          ) : (
            <ul className="list-inside list-disc space-y-1 text-sm text-slate-600">
              {twin.triage_reasons.map((reason, i) => (
                <li key={i}>{reason}</li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <TagListCard title="Conditions" items={twin.diseases} emptyText="None detected" />
        <TagListCard title="Medicines" items={twin.medicines} emptyText="None detected" />
        <TagListCard title="Symptoms" items={twin.symptoms} emptyText="None detected" />
      </div>

      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-slate-700">Latest report</h3>
        </CardHeader>
        <CardBody>
          {twin.latest_report_filename ? (
            <p className="text-sm text-slate-600">
              {twin.latest_report_filename}
              {twin.latest_report_date && (
                <span className="text-slate-400"> — {formatDateTime(twin.latest_report_date)}</span>
              )}
            </p>
          ) : (
            <p className="text-sm text-slate-400">No reports on file yet.</p>
          )}
          <p className="mt-2 text-xs text-slate-400">
            {twin.timeline_event_count} timeline event(s) tracked across all reports.
          </p>
        </CardBody>
      </Card>
    </div>
  );
}

function TagListCard({ title, items, emptyText }: { title: string; items: string[]; emptyText: string }) {
  return (
    <Card>
      <CardHeader>
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
      </CardHeader>
      <CardBody>
        {items.length === 0 ? (
          <p className="text-sm text-slate-400">{emptyText}</p>
        ) : (
          <div className="flex flex-wrap gap-1.5">
            {items.map((item) => (
              <Badge key={item} tone="neutral">
                {item}
              </Badge>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
}
