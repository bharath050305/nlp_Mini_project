import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { patientsApi } from "@/api/patients";
import Card, { CardBody } from "@/components/ui/Card";
import { SelectInput } from "@/components/ui/FormField";
import AudioUploader from "@/components/transcripts/AudioUploader";
import { FullPageSpinner } from "@/components/ui/Spinner";

export default function TranscriptUploadPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const preselected = searchParams.get("patientId");
  const [patientId, setPatientId] = useState<string>(preselected ?? "");

  const patientsQuery = useQuery({ queryKey: ["patients"], queryFn: patientsApi.list });

  if (patientsQuery.isLoading) return <FullPageSpinner />;
  const patients = patientsQuery.data ?? [];

  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">Upload Consultation</h1>
        <p className="text-sm text-slate-500">
          Choose a patient, then upload the consultation audio to generate a draft SOAP note.
        </p>
      </div>

      <Card>
        <CardBody className="flex flex-col gap-4">
          <SelectInput
            label="Patient"
            value={patientId}
            onChange={(e) => setPatientId(e.target.value)}
          >
            <option value="">Select a patient...</option>
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </SelectInput>

          {patientId ? (
            <AudioUploader
              patientId={Number(patientId)}
              onUploaded={(t) => navigate(`/doctor/transcripts/${t.id}`)}
            />
          ) : (
            <p className="text-sm text-slate-400">Select a patient to continue.</p>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
