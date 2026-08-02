import type { TimelineEvent } from "@/api/types";
import Card, { CardBody } from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDateTime } from "@/utils/format";

export default function TimelineView({ events }: { events: TimelineEvent[] }) {
  if (events.length === 0) {
    return (
      <EmptyState
        title="No timeline events yet"
        description="Upload a report to start building this patient's condition history."
      />
    );
  }

  return (
    <ol className="flex flex-col gap-4">
      {events.map((ev, i) => (
        <li key={i} className="relative pl-6">
          <span className="absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full bg-brand-500" />
          {i !== events.length - 1 && (
            <span className="absolute left-[4.5px] top-4 h-full w-px bg-slate-200" />
          )}
          <Card>
            <CardBody>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-medium text-slate-800">{ev.report_filename}</p>
                <span className="text-xs text-slate-400">{formatDateTime(ev.uploaded_at)}</span>
              </div>

              {ev.new_since_previous.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {ev.new_since_previous.map((n, j) => (
                    <Badge key={j} tone="warning">
                      new: {n}
                    </Badge>
                  ))}
                </div>
              )}

              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <TagGroup label="Diseases" items={ev.diseases} />
                <TagGroup label="Medicines" items={ev.medicines} />
                <TagGroup label="Lab values" items={ev.lab_values} />
              </div>
            </CardBody>
          </Card>
        </li>
      ))}
    </ol>
  );
}

function TagGroup({ label, items }: { label: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
      <div className="flex flex-wrap gap-1">
        {items.map((it, i) => (
          <span key={i} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {it}
          </span>
        ))}
      </div>
    </div>
  );
}
