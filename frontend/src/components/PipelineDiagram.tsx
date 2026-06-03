import { Upload, Eye, Layers, Gauge, Sparkles } from "lucide-react";
import type { ReactNode } from "react";

const STEPS: { label: string; icon: ReactNode }[] = [
  { label: "Upload", icon: <Upload className="h-4 w-4" /> },
  { label: "Saliency Model", icon: <Eye className="h-4 w-4" /> },
  { label: "Compression", icon: <Layers className="h-4 w-4" /> },
  { label: "Evaluation", icon: <Gauge className="h-4 w-4" /> },
  { label: "Result", icon: <Sparkles className="h-4 w-4" /> },
];

export function PipelineDiagram({ activeIndex }: { activeIndex?: number }) {
  return (
    <div
      className="w-full rounded-2xl border border-border bg-card/60 p-4 backdrop-blur sm:p-6"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-widest text-muted-foreground">Pipeline</span>
        <span className="text-[10px] uppercase tracking-widest text-muted-foreground">5 stages</span>
      </div>
      <ol className="flex flex-wrap items-center gap-y-3 sm:flex-nowrap sm:gap-y-0">
        {STEPS.map((s, i) => {
          const active = activeIndex !== undefined && i === activeIndex;
          const done = activeIndex !== undefined && i < activeIndex;
          const reached = done || active;
          return (
            <li key={s.label} className="flex min-w-0 flex-1 items-center">
              <div className="flex min-w-0 flex-col items-center text-center sm:flex-row sm:items-center sm:gap-2 sm:text-left">
                <div
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border transition-all ${
                    reached
                      ? "border-transparent text-primary-foreground"
                      : "border-border bg-card text-muted-foreground"
                  } ${active ? "animate-pulse" : ""}`}
                  style={reached ? { backgroundImage: "var(--gradient-primary)" } : undefined}
                >
                  {s.icon}
                </div>
                <span
                  className={`mt-1 text-[11px] font-medium sm:mt-0 sm:text-xs ${
                    reached ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className="mx-2 h-px flex-1 bg-border sm:mx-3">
                  <div
                    className="h-px transition-all duration-500"
                    style={{
                      width: done ? "100%" : active ? "50%" : "0%",
                      backgroundImage: "var(--gradient-primary)",
                    }}
                  />
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}