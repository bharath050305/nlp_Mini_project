import { useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { reportsApi } from "@/api/reports";
import { getErrorMessage } from "@/api/client";
import Button from "@/components/ui/Button";

export default function ReportUploader({ patientId }: { patientId: number }) {
  const [file, setFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (f: File) => reportsApi.upload(patientId, f),
    onSuccess: () => {
      toast.success("Report uploaded and queued for analysis");
      setFile(null);
      if (inputRef.current) inputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["reports", patientId] });
      queryClient.invalidateQueries({ queryKey: ["timeline", patientId] });
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  });

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-dashed border-slate-300 bg-slate-50/60 p-5">
      <div>
        <p className="text-sm font-medium text-slate-700">Upload a medical report</p>
        <p className="text-xs text-slate-400">PDF files only.</p>
      </div>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        className="text-sm text-slate-600 file:mr-3 file:rounded-lg file:border-0 file:bg-brand-600 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-white hover:file:bg-brand-700"
      />
      <Button
        onClick={() => file && mutation.mutate(file)}
        disabled={!file}
        loading={mutation.isPending}
        className="self-start"
      >
        Upload report
      </Button>
    </div>
  );
}
