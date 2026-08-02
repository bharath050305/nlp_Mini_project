import { useRef, useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { chatApi } from "@/api/chat";
import { getErrorMessage } from "@/api/client";
import MessageBubble from "./MessageBubble";
import type { ChatMessage } from "./MessageBubble";
import Button from "@/components/ui/Button";
import Spinner from "@/components/ui/Spinner";

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `msg-${idCounter}-${Date.now()}`;
}

export default function ChatWindow({ patientId }: { patientId: number }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (message: string) => chatApi.send(patientId, message),
  });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, mutation.isPending]);

  function handleSend() {
    const text = input.trim();
    if (!text || mutation.isPending) return;
    setMessages((prev) => [...prev, { id: nextId(), role: "user", text }]);
    setInput("");
    mutation.mutate(text, {
      onSuccess: (result) => {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", text: result.final_response, result },
        ]);
      },
      onError: (err) => {
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", text: `Error: ${getErrorMessage(err)}` },
        ]);
      },
    });
  }

  return (
    <div className="flex h-[600px] flex-col rounded-xl border border-slate-200 bg-slate-50">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center text-sm text-slate-400">
            <p className="font-medium text-slate-500">Ask MediAgent anything</p>
            <p className="mt-1 max-w-xs">
              "Summarize my latest report", "Any drug interactions?", "Set a reminder for
              metformin twice daily"
            </p>
          </div>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {mutation.isPending && (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <Spinner className="h-4 w-4" />
            MediAgent is thinking...
          </div>
        )}
      </div>
      <div className="border-t border-slate-200 bg-white p-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder="Type a message..."
            rows={1}
            className="max-h-32 flex-1 resize-none rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-brand-400 focus:outline-none focus:ring-2 focus:ring-brand-100"
          />
          <Button onClick={handleSend} loading={mutation.isPending} disabled={!input.trim()}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
