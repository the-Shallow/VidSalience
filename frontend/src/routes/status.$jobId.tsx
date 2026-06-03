import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, AlertTriangle, Clock, Cpu, Upload, ArrowRight } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { PipelineDiagram } from "@/components/PipelineDiagram";
import { getJob, type Job, type JobStatus } from "@/lib/api";

// export const Route = createFileRoute("/status/$jobId")({
//   head: () => ({
//     meta: [{ title: "Processing — VidSalience" }],
//   }),
//   component: StatusPage,
// });

const STAGES: { key: JobStatus; label: string; icon: React.ReactNode }[] = [
  { key: "UPLOADED", label: "Uploaded", icon: <Upload className="h-4 w-4" /> },
  { key: "QUEUED", label: "Queued", icon: <Clock className="h-4 w-4" /> },
  { key: "PROCESSING", label: "Processing", icon: <Cpu className="h-4 w-4" /> },
  { key: "COMPLETED", label: "Completed", icon: <CheckCircle2 className="h-4 w-4" /> },
];

const ORDER: JobStatus[] = ["UPLOADED", "QUEUED", "PROCESSING", "COMPLETED"];

const PIPELINE_INDEX: Record<JobStatus, number> = {
  UPLOADED: 0,
  QUEUED: 1,
  PROCESSING: 2,
  COMPLETED: 4,
  FAILED: 2,
};

function StatusPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;

    async function tick() {
      try {
        const j = await getJob(jobId);
        if (!active) return;
        setJob(j);
        setError(null);
        if (j.status === "COMPLETED") {
          setTimeout(() => {
            if (active) navigate(`/results/${jobId}`);;
          }, 1500);
          return;
        }
        if (j.status === "FAILED") return;
      } catch (e) {
        if (!active) return;
        setError(e instanceof Error ? e.message : "Failed to fetch job");
      }
      timer = setTimeout(tick, 3000);
    }
    tick();

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [jobId, navigate]);

  const currentIdx = job ? ORDER.indexOf(job.status as JobStatus) : -1;
  const failed = job?.status === "FAILED";
  const completed = job?.status === "COMPLETED";

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-16">
        <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">Job</div>
        <h1 className="font-mono text-sm sm:text-lg break-all">{jobId}</h1>

        <div className="mt-6">
          <PipelineDiagram activeIndex={job ? PIPELINE_INDEX[job.status] : undefined} />
        </div>

        <div className="mt-6 rounded-2xl border border-border bg-card p-6 sm:p-8" style={{ boxShadow: "var(--shadow-card)" }}>
          <div className="flex flex-wrap items-center gap-3">
            <StatusBadge status={job?.status} />
            {job?.original_filename && (
              <span className="text-sm text-muted-foreground truncate">{job.original_filename}</span>
            )}
          </div>

          <div className="mt-10">
            <ol className="grid grid-cols-4 gap-2">
              {STAGES.map((stage, i) => {
                const reached = !failed && currentIdx >= i;
                const active = !failed && currentIdx === i && !completed;
                return (
                  <li key={stage.key} className="flex flex-col items-center text-center">
                    <div
                      className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-all ${
                        reached
                          ? "border-primary text-primary-foreground"
                          : "border-border bg-card text-muted-foreground"
                      }`}
                      style={reached ? { backgroundImage: "var(--gradient-primary)" } : undefined}
                    >
                      {active ? <Loader2 className="h-4 w-4 animate-spin" /> : stage.icon}
                    </div>
                    <span className={`mt-2 text-xs ${reached ? "text-foreground font-medium" : "text-muted-foreground"}`}>
                      {stage.label}
                    </span>
                  </li>
                );
              })}
            </ol>
            <div className="relative mt-[-44px] mx-5 h-0.5 bg-border -z-0">
              <div
                className="h-0.5 transition-all duration-500"
                style={{
                  width: `${Math.max(0, currentIdx) / (ORDER.length - 1) * 100}%`,
                  backgroundImage: "var(--gradient-primary)",
                }}
              />
            </div>
          </div>

          {failed && (
            <div className="mt-10 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
              <div>
                <p className="font-medium text-destructive">Processing failed</p>
                <p className="mt-1 text-destructive/80">{job?.error_message || "An unknown error occurred."}</p>
              </div>
            </div>
          )}

          {completed && (
            <div className="mt-10 flex flex-col items-center gap-3 text-center">
              <p className="text-sm text-muted-foreground">Compression complete — redirecting to results…</p>
              <Button asChild>
                <Link to="/results/$jobId" params={{ jobId }}>
                  View results <ArrowRight className="ml-1.5 h-4 w-4" />
                </Link>
              </Button>
            </div>
          )}

          {!job && !error && (
            <div className="mt-10 flex items-center justify-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading job…
            </div>
          )}

          {error && !job && (
            <div className="mt-10 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          )}
        </div>

        <div className="mt-6 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
            Polling every 3 seconds
          </span>
          {job && <span>Updated {new Date(job.updated_at).toLocaleTimeString()}</span>}
        </div>
      </main>
    </div>
  );
}


export default StatusPage;