import { useRef, useState } from "react";
import clsx from "clsx";

interface VoiceRecorderButtonProps {
  onRecorded: (audioBlob: Blob) => void;
  disabled?: boolean;
}

/**
 * Records a short voice message via the browser's MediaRecorder API and
 * hands the resulting blob to the caller on stop — the caller (ChatWindow)
 * posts it to POST /api/patients/{id}/chat/voice, which reuses the same
 * Whisper pipeline built for transcript-to-report.
 */
export default function VoiceRecorderButton({ onRecorded, disabled }: VoiceRecorderButtonProps) {
  const [recording, setRecording] = useState(false);
  const [unsupported, setUnsupported] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setUnsupported(true);
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
        onRecorded(blob);
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
    } catch {
      setUnsupported(true);
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setRecording(false);
  }

  if (unsupported) {
    return (
      <span className="text-xs text-slate-400" title="Voice input needs microphone access in a supported browser">
        Voice unavailable
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={recording ? stopRecording : startRecording}
      disabled={disabled}
      aria-label={recording ? "Stop recording" : "Record a voice message"}
      title={recording ? "Stop recording" : "Record a voice message"}
      className={clsx(
        "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-colors",
        recording
          ? "animate-pulse border-rose-300 bg-rose-50 text-rose-600"
          : "border-slate-200 text-slate-500 hover:bg-slate-100",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <MicIcon />
    </button>
  );
}

function MicIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" strokeLinecap="round" />
      <path d="M12 19v3" strokeLinecap="round" />
    </svg>
  );
}
