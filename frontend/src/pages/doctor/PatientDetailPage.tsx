import { useParams, useNavigate, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { patientsApi } from "@/api/patients";
import { reportsApi } from "@/api/reports";
import { remindersApi } from "@/api/reminders";
import { interactionsApi } from "@/api/interactions";
import { transcriptsApi } from "@/api/transcripts";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Tabs from "@/components/ui/Tabs";
import Card, { CardBody } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ReportUploader from "@/components/reports/ReportUploader";
import ReportList from "@/components/reports/ReportList";
import InteractionsPanel from "@/components/reports/InteractionsPanel";
import ReminderList from "@/components/reminders/ReminderList";
import TimelineView from "@/components/timeline/TimelineView";
import ChatWindow from "@/components/chat/ChatWindow";
import AnalyticsPanel from "@/components/analytics/AnalyticsPanel";
import DigitalTwinPanel from "@/components/twin/DigitalTwinPanel";
import { StatusBadge } from "@/components/ui/Badge";
import EmptyState from "@/components/ui/EmptyState";
import { formatDateTime } from "@/utils/format";

export default function PatientDetailPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const id = Number(patientId);
  const navigate = useNavigate();

  const patientQuery = useQuery({
    queryKey: ["patient", id],
    queryFn: () => patientsApi.get(id),
    enabled: !!id,
  });

  if (patientQuery.isLoading) return <FullPageSpinner />;
  if (patientQuery.isError || !patientQuery.data) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-rose-600">
            You don't have access to this patient, or they don't exist.
          </p>
          <Button variant="secondary" className="mt-3" onClick={() => navigate(-1)}>
            Go back
          </Button>
        </CardBody>
      </Card>
    );
  }

  const patient = patientQuery.data;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">{patient.name}</h1>
          <p className="text-sm text-slate-500">
            {patient.date_of_birth ? `DOB ${patient.date_of_birth}` : "DOB unknown"}
            {patient.phone ? ` · ${patient.phone}` : ""}
          </p>
        </div>
        <Link to={`/doctor/transcripts/upload?patientId=${patient.id}`}>
          <Button variant="secondary">Upload consultation audio</Button>
        </Link>
      </div>

      <Tabs
        tabs={[
          { key: "chat", label: "Chat", content: <ChatWindow patientId={patient.id} /> },
          {
            key: "digital-twin",
            label: "Digital Twin",
            content: <DigitalTwinPanel patientId={patient.id} />,
          },
          { key: "reports", label: "Reports", content: <ReportsTab patientId={patient.id} /> },
          {
            key: "analytics",
            label: "Analytics",
            content: <AnalyticsPanel patientId={patient.id} />,
          },
          {
            key: "timeline",
            label: "Timeline",
            content: <TimelineTab patientId={patient.id} />,
          },
          {
            key: "interactions",
            label: "Interactions",
            content: <InteractionsTab patientId={patient.id} />,
          },
          {
            key: "reminders",
            label: "Reminders",
            content: <RemindersTab patientId={patient.id} />,
          },
          {
            key: "consultations",
            label: "Consultations",
            content: <ConsultationsTab patientId={patient.id} />,
          },
        ]}
      />
    </div>
  );
}

function ReportsTab({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["reports", patientId],
    queryFn: () => reportsApi.list(patientId),
  });
  return (
    <div className="flex flex-col gap-5">
      <ReportUploader patientId={patientId} />
      {query.isLoading ? <FullPageSpinner /> : <ReportList patientId={patientId} reports={query.data ?? []} />}
    </div>
  );
}

function TimelineTab({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["timeline", patientId],
    queryFn: () => reportsApi.timeline(patientId),
  });
  if (query.isLoading) return <FullPageSpinner />;
  return <TimelineView events={query.data ?? []} />;
}

function InteractionsTab({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["interactions", patientId],
    queryFn: () => interactionsApi.list(patientId),
  });
  if (query.isLoading) return <FullPageSpinner />;
  return <InteractionsPanel warnings={query.data ?? []} />;
}

function RemindersTab({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["reminders", patientId],
    queryFn: () => remindersApi.list(patientId),
  });
  if (query.isLoading) return <FullPageSpinner />;
  return <ReminderList patientId={patientId} reminders={query.data ?? []} />;
}

function ConsultationsTab({ patientId }: { patientId: number }) {
  const query = useQuery({
    queryKey: ["transcripts", patientId],
    queryFn: () => transcriptsApi.listForPatient(patientId),
  });
  if (query.isLoading) return <FullPageSpinner />;
  const transcripts = query.data ?? [];
  if (transcripts.length === 0) {
    return (
      <EmptyState
        title="No consultations recorded yet"
        description="Upload a consultation audio recording to generate a draft SOAP note."
      />
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {transcripts.map((t) => (
        <Link key={t.id} to={`/doctor/transcripts/${t.id}`}>
          <Card className="transition-shadow hover:shadow-md">
            <CardBody className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-slate-800">{t.audio_filename}</p>
                <p className="text-xs text-slate-400">{formatDateTime(t.created_at)}</p>
              </div>
              <StatusBadge status={t.status} />
            </CardBody>
          </Card>
        </Link>
      ))}
    </div>
  );
}
