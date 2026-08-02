import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import type { SoapNoteOut } from "@/api/types";
import { transcriptsApi } from "@/api/transcripts";
import { getErrorMessage } from "@/api/client";
import { TextAreaInput } from "@/components/ui/FormField";
import Button from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/Badge";

export default function SoapNoteEditor({ soap }: { soap: SoapNoteOut }) {
  const queryClient = useQueryClient();
  const isDraft = soap.status === "draft";

  const [subjective, setSubjective] = useState(soap.subjective ?? "");
  const [objective, setObjective] = useState(soap.objective ?? "");
  const [assessment, setAssessment] = useState(soap.assessment ?? "");
  const [plan, setPlan] = useState(soap.plan ?? "");

  useEffect(() => {
    setSubjective(soap.subjective ?? "");
    setObjective(soap.objective ?? "");
    setAssessment(soap.assessment ?? "");
    setPlan(soap.plan ?? "");
  }, [soap]);

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["soap", soap.transcript_id] });

  const saveMutation = useMutation({
    mutationFn: () =>
      transcriptsApi.updateSoap(soap.transcript_id, { subjective, objective, assessment, plan }),
    onSuccess: () => {
      toast.success("Draft saved");
      invalidate();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  const finalizeMutation = useMutation({
    mutationFn: () => transcriptsApi.finalize(soap.transcript_id),
    onSuccess: () => {
      toast.success("Note finalized and added to patient timeline");
      invalidate();
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <p className="text-sm font-medium text-slate-700">SOAP note</p>
        <StatusBadge status={soap.status} />
      </div>

      <TextAreaInput
        label="Subjective"
        value={subjective}
        onChange={(e) => setSubjective(e.target.value)}
        disabled={!isDraft}
        rows={4}
      />
      <TextAreaInput
        label="Objective"
        value={objective}
        onChange={(e) => setObjective(e.target.value)}
        disabled={!isDraft}
        rows={4}
      />
      <TextAreaInput
        label="Assessment"
        value={assessment}
        onChange={(e) => setAssessment(e.target.value)}
        disabled={!isDraft}
        rows={4}
      />
      <TextAreaInput
        label="Plan"
        value={plan}
        onChange={(e) => setPlan(e.target.value)}
        disabled={!isDraft}
        rows={4}
      />

      {isDraft && (
        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={() => saveMutation.mutate()} loading={saveMutation.isPending}>
            Save draft
          </Button>
          <Button
            onClick={() => {
              if (confirm("Finalize this note? Editing will be locked afterwards.")) {
                finalizeMutation.mutate();
              }
            }}
            loading={finalizeMutation.isPending}
          >
            Finalize note
          </Button>
        </div>
      )}
    </div>
  );
}
