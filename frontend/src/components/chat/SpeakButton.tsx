import { useEffect, useState } from "react";

/**
 * Reads `text` aloud via the browser's built-in SpeechSynthesis API —
 * purely client-side, no backend TTS dependency. Toggles between
 * speak/stop; automatically stops if another SpeakButton starts speaking
 * or the component unmounts mid-utterance.
 */
export default function SpeakButton({ text }: { text: string }) {
  const [speaking, setSpeaking] = useState(false);
  const supported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    return () => {
      if (speaking) window.speechSynthesis.cancel();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (!supported) return null;

  function toggle() {
    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }
    window.speechSynthesis.cancel(); // stop any other utterance first
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setSpeaking(true);
  }

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={speaking ? "Stop reading aloud" : "Read this response aloud"}
      title={speaking ? "Stop reading aloud" : "Read this response aloud"}
      className="inline-flex h-6 w-6 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"
    >
      {speaking ? <StopIcon /> : <SpeakerIcon />}
    </button>
  );
}

function SpeakerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M5 9v6h4l5 5V4l-5 5H5z" strokeLinejoin="round" />
      <path d="M17.5 8.5a5 5 0 0 1 0 7" strokeLinecap="round" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <rect x="6" y="6" width="12" height="12" rx="1.5" />
    </svg>
  );
}
