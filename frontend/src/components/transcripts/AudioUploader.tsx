import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { transcriptsApi } from "@/api/transcripts";
import { getErrorMessage } from "@/api/client";
import Button from "@/components/ui/Button";
import type { TranscriptOut } from "@/api/types";

export default function AudioUploader({
  patientId,
  onUploaded,
}: {
  patientId: number;
  onUploaded: (transcript: TranscriptOut) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const mutation = useMutation({
    mutationFn: (f: File) => transcriptsApi.upload(patientId, f),
    onSuccess: (transcript) => {
      toast.success("Audio uploaded — processing started");
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      onUploaded(transcript);
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50/60 p-5">
      <div>
        <p className="text-sm font-medium text-slate-700">Upload consultation audio</p>
        <p className="text-xs text-slate-400">
          Record the consultation and upload the audio file to generate a draft SOAP note.
        </p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="audio/*"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700"
      />
      <Button
        onClick={() => file && mutation.mutate(file)}
        disabled={!file}
        loading={mutation.isPending}
        className="self-start"
      >
        Upload &amp; process
      </Button>
    </div>
  );
}
