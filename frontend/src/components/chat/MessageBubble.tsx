import type { AgentRunResult } from "@/api/types";
import ExecutionTimeline from "./ExecutionTimeline";
import EvidenceCard from "./EvidenceCard";
import SpeakButton from "./SpeakButton";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: AgentRunResult;
  viaVoice?: boolean;
}

export default function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] ${isUser ? "order-1" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm ${
            isUser
              ? "rounded-br-sm bg-brand-600 text-white"
              : "rounded-bl-sm border border-slate-200 bg-white text-slate-700"
          }`}
        >
          {isUser && message.viaVoice && (
            <p className="mb-1 flex items-center gap-1 text-[11px] font-medium uppercase tracking-wide text-brand-100">
              <MicIcon /> Voice message
            </p>
          )}
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
        {!isUser && (
          <div className="mt-1 flex items-center gap-1 pl-1">
            <SpeakButton text={message.text} />
          </div>
        )}
        {message.result && (
          <div className="mt-1">
            <ExecutionTimeline log={message.result.execution_log} />
            <EvidenceCard result={message.result} />
          </div>
        )}
      </div>
    </div>
  );
}

function MicIcon() {
  return (
    <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" strokeLinecap="round" />
    </svg>
  );
}
