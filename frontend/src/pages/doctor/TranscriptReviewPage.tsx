import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { transcriptsApi } from "@/api/transcripts";
import { FullPageSpinner } from "@/components/ui/Spinner";
import Card, { CardBody } from "@/components/ui/Card";
import TranscriptStatus from "@/components/transcripts/TranscriptStatus";
import SoapNoteEditor from "@/components/transcripts/SoapNoteEditor";

const terminalStatuses = new Set(["draft_ready", "finalized", "failed"]);
const soapReadyStatuses = new Set(["draft_ready", "finalized"]);

export default function TranscriptReviewPage() {
  const { transcriptId } = useParams<{ transcriptId: string }>();
  const id = Number(transcriptId);

  const transcriptQuery = useQuery({
    queryKey: ["transcript", id],
    queryFn: () => transcriptsApi.get(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && terminalStatuses.has(status) ? false : 3000;
    },
  });

  const transcript = transcriptQuery.data;

  const soapQuery = useQuery({
    queryKey: ["soap", id],
    queryFn: () => transcriptsApi.getSoap(id),
    enabled: !!transcript && soapReadyStatuses.has(transcript.status),
  });

  if (transcriptQuery.isLoading || !transcript) return <FullPageSpinner />;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-800">{transcript.audio_filename}</h1>
        <p className="text-sm text-slate-500">Consultation review</p>
      </div>

      <div className="flex flex-col gap-4">
        <TranscriptStatus status={transcript.status} errorDetail={transcript.error_detail} />

        {soapReadyStatuses.has(transcript.status) && (
          <Card>
            <CardBody>
              {soapQuery.isLoading ? (
                <FullPageSpinner />
              ) : soapQuery.data ? (
                <SoapNoteEditor soap={soapQuery.data} />
              ) : (
                <p className="text-sm text-slate-400">SOAP note not available yet.</p>
              )}
            </CardBody>
          </Card>
        )}
      </div>
    </div>
  );
}
