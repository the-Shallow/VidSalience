import type { JobStatus } from "@/lib/api";
import { Loader2, CheckCircle2, AlertTriangle, Clock, Upload } from "lucide-react";
import type { ReactNode } from "react";

const CONFIG: Record<JobStatus | "LOADING", { label: string; cls: string; icon: ReactNode }> = {
  UPLOADED: {
    label: "Uploaded",
    cls: "bg-secondary text-secondary-foreground border-border",
    icon: <Upload className="h-3 w-3" />,
  },
  QUEUED: {
    label: "Queued",
    cls: "bg-[oklch(0.95_0.05_75)] text-[oklch(0.45_0.15_75)] border-[oklch(0.85_0.1_75)] dark:bg-[oklch(0.3_0.07_75)] dark:text-[oklch(0.85_0.15_75)] dark:border-[oklch(0.4_0.1_75)]",
    icon: <Clock className="h-3 w-3" />,
  },
  PROCESSING: {
    label: "Processing",
    cls: "bg-primary/10 text-primary border-primary/30",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
  COMPLETED: {
    label: "Completed",
    cls: "bg-[oklch(0.94_0.07_155)] text-[oklch(0.4_0.15_155)] border-[oklch(0.8_0.12_155)] dark:bg-[oklch(0.3_0.07_155)] dark:text-[oklch(0.85_0.17_155)] dark:border-[oklch(0.4_0.1_155)]",
    icon: <CheckCircle2 className="h-3 w-3" />,
  },
  FAILED: {
    label: "Failed",
    cls: "bg-destructive/10 text-destructive border-destructive/30",
    icon: <AlertTriangle className="h-3 w-3" />,
  },
  LOADING: {
    label: "Loading",
    cls: "bg-muted text-muted-foreground border-border",
    icon: <Loader2 className="h-3 w-3 animate-spin" />,
  },
};

export function StatusBadge({ status }: { status?: JobStatus }) {
  const v = CONFIG[status ?? "LOADING"];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${v.cls}`}
    >
      {v.icon}
      {v.label}
    </span>
  );
}