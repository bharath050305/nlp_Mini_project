import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { patientsApi } from "@/api/patients";
import { reportsApi } from "@/api/reports";
import { remindersApi } from "@/api/reminders";
import { interactionsApi } from "@/api/interactions";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Tabs from "@/components/ui/Tabs";
import Card, { CardBody } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import ReportList from "@/components/reports/ReportList";
import InteractionsPanel from "@/components/reports/InteractionsPanel";
import ReminderList from "@/components/reminders/ReminderList";
import TimelineView from "@/components/timeline/TimelineView";
import AnalyticsPanel from "@/components/analytics/AnalyticsPanel";

export default function NursePatientDetailPage() {
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
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">{patient.name}</h1>
        <p className="text-sm text-slate-500">
          {patient.date_of_birth ? `DOB ${patient.date_of_birth}` : "DOB unknown"}
          {patient.phone ? ` · ${patient.phone}` : ""}
        </p>
      </div>

      <Tabs
        tabs={[
          {
            key: "reminders",
            label: "Reminders",
            content: <RemindersTab patientId={patient.id} />,
          },
          {
            key: "analytics",
            label: "Analytics",
            content: <AnalyticsPanel patientId={patient.id} />,
          },
          {
            key: "timeline",
            label: "Timeline (previous conditions)",
            content: <TimelineTab patientId={patient.id} />,
          },
          { key: "reports", label: "Reports", content: <ReportsTab patientId={patient.id} /> },
          {
            key: "interactions",
            label: "Interactions",
            content: <InteractionsTab patientId={patient.id} />,
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
  if (query.isLoading) return <FullPageSpinner />;
  return <ReportList patientId={patientId} reports={query.data ?? []} />;
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
