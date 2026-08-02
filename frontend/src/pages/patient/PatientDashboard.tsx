import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { patientsApi } from "@/api/patients";
import { reportsApi } from "@/api/reports";
import { remindersApi } from "@/api/reminders";
import { interactionsApi } from "@/api/interactions";
import Tabs from "@/components/ui/Tabs";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import ReportUploader from "@/components/reports/ReportUploader";
import ReportList from "@/components/reports/ReportList";
import InteractionsPanel from "@/components/reports/InteractionsPanel";
import ChatWindow from "@/components/chat/ChatWindow";
import ReminderList from "@/components/reminders/ReminderList";
import ReminderForm from "@/components/reminders/ReminderForm";
import TimelineView from "@/components/timeline/TimelineView";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { getErrorMessage } from "@/api/client";
import toast from "react-hot-toast";

export default function PatientDashboard() {
  const patientQuery = useQuery({
    queryKey: ["patient", "me"],
    queryFn: patientsApi.me,
  });

  if (patientQuery.isLoading) return <FullPageSpinner />;

  if (patientQuery.isError || !patientQuery.data) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-rose-600">
            Could not load your patient record. Please try refreshing.
          </p>
        </CardBody>
      </Card>
    );
  }

  const patient = patientQuery.data;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">Hi, {patient.name}</h1>
        <p className="text-sm text-slate-500">
          Manage your reports, medicines, and talk to MediAgent.
        </p>
      </div>

      <Tabs
        tabs={[
          { key: "chat", label: "Chat", content: <ChatWindow patientId={patient.id} /> },
          { key: "reports", label: "Reports", content: <ReportsTab patientId={patient.id} /> },
          {
            key: "reminders",
            label: "Reminders",
            content: <RemindersTab patientId={patient.id} />,
          },
          { key: "timeline", label: "Timeline", content: <TimelineTab patientId={patient.id} /> },
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
  return (
    <div className="flex flex-col gap-5">
      <ReportUploader patientId={patientId} />
      {query.isLoading ? <FullPageSpinner /> : <ReportList patientId={patientId} reports={query.data ?? []} />}
    </div>
  );
}

function RemindersTab({ patientId }: { patientId: number }) {
  const [formOpen, setFormOpen] = useState(false);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ["reminders", patientId],
    queryFn: () => remindersApi.list(patientId),
  });

  const createMutation = useMutation({
    mutationFn: (payload: Parameters<typeof remindersApi.create>[1]) =>
      remindersApi.create(patientId, payload),
    onSuccess: () => {
      toast.success("Reminder created");
      setFormOpen(false);
      queryClient.invalidateQueries({ queryKey: ["reminders", patientId] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button onClick={() => setFormOpen(true)}>+ Add reminder</Button>
      </div>
      {query.isLoading ? (
        <FullPageSpinner />
      ) : (
        <ReminderList
          patientId={patientId}
          reminders={query.data ?? []}
          onAddClick={() => setFormOpen(true)}
        />
      )}
      <Modal open={formOpen} onClose={() => setFormOpen(false)} title="Add a reminder">
        <ReminderForm
          submitting={createMutation.isPending}
          onCancel={() => setFormOpen(false)}
          onSubmit={(payload) => createMutation.mutate(payload)}
        />
      </Modal>
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
