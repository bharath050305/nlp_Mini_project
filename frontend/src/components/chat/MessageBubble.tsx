import type { AgentRunResult } from "@/api/types";
import ExecutionTimeline from "./ExecutionTimeline";
import EvidenceCard from "./EvidenceCard";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  result?: AgentRunResult;
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
          <p className="whitespace-pre-wrap">{message.text}</p>
        </div>
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
