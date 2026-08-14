import type { ReactNode } from "react";
import clsx from "clsx";
import type { Autonomy, RiskTier } from "@/api/types";

type Tone = "neutral" | "brand" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-600",
  brand: "bg-brand-100 text-brand-700",
  success: "bg-emerald-100 text-emerald-700",
  warning: "bg-amber-100 text-amber-800",
  danger: "bg-rose-100 text-rose-700",
  info: "bg-sky-100 text-sky-700",
};

export default function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        toneClasses[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function AutonomyBadge({ autonomy }: { autonomy: Autonomy | null }) {
  if (!autonomy) return null;
  const tone: Tone = autonomy === "A0" ? "neutral" : autonomy === "A1" ? "info" : "brand";
  return <Badge tone={tone}>{autonomy}</Badge>;
}

export function RiskBadge({ risk }: { risk: RiskTier | null }) {
  if (!risk) return null;
  const tone: Tone =
    risk === "R0" ? "success" : risk === "R1" ? "success" : risk === "R2" ? "warning" : "danger";
  return <Badge tone={tone}>{risk}</Badge>;
}

export function TriageBadge({ level }: { level: "low" | "medium" | "high" | "critical" | string }) {
  const tone: Tone =
    level === "critical" ? "danger" : level === "high" ? "danger" : level === "medium" ? "warning" : "success";
  return <Badge tone={tone}>{level.toUpperCase()}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, Tone> = {
    done: "success",
    finalized: "success",
    sent: "success",
    running: "info",
    transcribing: "info",
    structuring: "info",
    pending: "neutral",
    uploaded: "neutral",
    draft: "neutral",
    draft_ready: "brand",
    transcribed: "info",
    skipped: "neutral",
    failed: "danger",
    read: "neutral",
  };
  return <Badge tone={map[status] ?? "neutral"}>{status.replace(/_/g, " ")}</Badge>;
}
