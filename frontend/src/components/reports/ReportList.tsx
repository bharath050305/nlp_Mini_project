import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import type { ReportOut, ReportDetailOut, EntitiesJson, SummaryJson } from "@/api/types";
import { reportsApi } from "@/api/reports";
import Card, { CardBody } from "@/components/ui/Card";
import Modal from "@/components/ui/Modal";
import Badge from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import Spinner from "@/components/ui/Spinner";
import { formatDateTime, safeJsonParse } from "@/utils/format";

export default function ReportList({
  patientId,
  reports,
}: {
  patientId: number;
  reports: ReportOut[];
}) {
  const [selected, setSelected] = useState<ReportOut | null>(null);

  if (reports.length === 0) {
    return (
      <EmptyState
        title="No reports yet"
        description="Uploaded medical reports will appear here once processed."
      />
    );
  }

  return (
    <>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {reports.map((r) => (
          <button key={r.id} onClick={() => setSelected(r)} className="text-left">
            <Card className="transition-shadow hover:shadow-md">
              <CardBody>
                <p className="font-medium text-slate-800">{r.filename}</p>
                <div className="mt-1 flex items-center gap-2">
                  <Badge tone="brand">{r.source_type}</Badge>
                  <span className="text-xs text-slate-400">{formatDateTime(r.created_at)}</span>
                </div>
              </CardBody>
            </Card>
          </button>
        ))}
      </div>

      <Modal
        open={!!selected}
        onClose={() => setSelected(null)}
        title={selected?.filename}
        widthClassName="max-w-2xl"
      >
        {selected && <ReportDetail patientId={patientId} reportId={selected.id} />}
      </Modal>
    </>
  );
}

function ReportDetail({ patientId, reportId }: { patientId: number; reportId: number }) {
  const { data, isLoading } = useQuery<ReportDetailOut>({
    queryKey: ["report", patientId, reportId],
    queryFn: () => reportsApi.get(patientId, reportId),
  });

  if (isLoading || !data) {
    return (
      <div className="flex justify-center py-8">
        <Spinner />
      </div>
    );
  }

  const summary = safeJsonParse<SummaryJson>(data.summary_json);
  const entities = safeJsonParse<EntitiesJson>(data.entities_json);

  return (
    <div className="flex flex-col gap-4">
      {summary && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Summary
          </p>
          <p className="text-sm text-slate-700">{summary.patient_summary}</p>
          {summary.key_findings.length > 0 && (
            <ul className="ml-4 mt-2 list-disc text-sm text-slate-600">
              {summary.key_findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {entities && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <EntityGroup label="Diseases" items={entities.diseases} />
          <EntityGroup label="Medicines" items={entities.medicines} />
          <EntityGroup label="Symptoms" items={entities.symptoms} />
          <EntityGroup label="Lab tests" items={entities.lab_tests} />
          <EntityGroup label="Lab values" items={entities.lab_values} />
          <EntityGroup label="Dosages" items={entities.dosages} />
        </div>
      )}

      <details className="rounded-lg border border-slate-100 bg-slate-50/70 p-3">
        <summary className="cursor-pointer text-xs font-medium text-slate-500">
          View raw extracted text
        </summary>
        <p className="mt-2 max-h-64 overflow-y-auto whitespace-pre-wrap text-xs text-slate-500">
          {data.raw_text}
        </p>
      </details>
    </div>
  );
}

function EntityGroup({ label, items }: { label: string; items: string[] }) {
  if (!items || items.length === 0) return null;
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
