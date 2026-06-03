import { Link, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Download, Upload, Loader2, AlertCircle, TrendingDown, Gauge, Activity, Eye, HardDrive, Database, Zap } from "lucide-react";
import type { ReactNode } from "react";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { getResults, type JobResult } from "@/lib/api";

// export const Route = createFileRoute("/results/$jobId")({
//   head: () => ({
//     meta: [{ title: "Results — VidSalience" }],
//   }),
//   component: ResultsPage,
// });

function ResultsPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getResults(jobId)
      .then((r) => active && setData(r))
      .catch((e) => active && setError(e instanceof Error ? e.message : "Failed to load results"));
    return () => {
      active = false;
    };
  }, [jobId]);

  console.log("Results data:", data, "Error:", error);
  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-12">
        {!data && !error && <ResultsSkeleton />}
        {error && (
          <div className="flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {data && <ResultsContent data={data} />}
      </main>
    </div>
  );
}

function ResultsSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-4 w-32 rounded bg-muted" />
      <div className="mt-3 h-8 w-72 max-w-full rounded bg-muted" />
      <div className="mt-8 h-40 rounded-2xl bg-muted/60" />
      <div className="mt-8 aspect-video w-full rounded-2xl bg-muted/60" />
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-32 rounded-2xl bg-muted/60" />
        ))}
      </div>
    </div>
  );
}

function ResultsContent({ data }: { data: JobResult }) {
  const m = data.metrics;
  const reduction =
    m.original_size_mb > 0 ? ((m.original_size_mb - m.compressed_size_mb) / m.original_size_mb) * 100 : 0;

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="text-xs uppercase tracking-widest text-muted-foreground">Compression Complete</div>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{data.original_filename}</h1>
          <p className="mt-1 font-mono text-xs text-muted-foreground break-all">{data.job_id}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link to="/upload">
              <Upload className="mr-1.5 h-4 w-4" /> Upload Another
            </Link>
          </Button>
          <Button asChild>
            <a href={data.download_url} download>
              <Download className="mr-1.5 h-4 w-4" /> Download
            </a>
          </Button>
        </div>
      </div>

      {/* Highlight reduction */}
      <div
        className="mt-8 overflow-hidden rounded-2xl border border-border p-8"
        style={{ backgroundImage: "var(--gradient-subtle)", boxShadow: "var(--shadow-card)" }}
      >
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <TrendingDown className="h-4 w-4 text-[color:var(--success)]" /> Size reduction
            </div>
            <div className="mt-2 text-5xl font-semibold tracking-tight">
              <span className="bg-clip-text text-transparent" style={{ backgroundImage: "var(--gradient-primary)" }}>
                {reduction.toFixed(1)}%
              </span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {m.original_size_mb.toFixed(2)} MB → {m.compressed_size_mb.toFixed(2)} MB
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:gap-6">
            <MiniStat label="Original" value={`${m.original_size_mb.toFixed(2)} MB`} />
            <MiniStat label="Compressed" value={`${m.compressed_size_mb.toFixed(2)} MB`} />
          </div>
        </div>
      </div>

      {/* Video */}
      <div className="mt-8 overflow-hidden rounded-2xl border border-border bg-card" style={{ boxShadow: "var(--shadow-card)" }}>
        <video
          src={data.download_url}
          controls
          className="aspect-video w-full bg-black"
        />
      </div>

      {/* Metrics grid */}
      <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard icon={<Gauge className="h-4 w-4" />} label="PSNR" value={m.average_psnr.toFixed(2)} unit="dB" hint="Pixel-level fidelity" />
        <MetricCard icon={<Activity className="h-4 w-4" />} label="SSIM" value={m.average_ssim.toFixed(4)} hint="Structural similarity" />
        <MetricCard
          icon={<Eye className="h-4 w-4" />}
          label="Saliency-weighted PSNR"
          value={m.average_saliency_weighted_psnr.toFixed(2)}
          unit="dB"
          hint="Quality where it matters"
          highlight
        />
        <MetricCard icon={<HardDrive className="h-4 w-4" />} label="Original Size" value={m.original_size_mb.toFixed(2)} unit="MB" />
        <MetricCard icon={<Database className="h-4 w-4" />} label="Compressed Size" value={m.compressed_size_mb.toFixed(2)} unit="MB" />
        <MetricCard icon={<Zap className="h-4 w-4" />} label="Bitrate" value={m.compressed_bitrate_kbps.toFixed(0)} unit="kbps" />
      </div>
    </>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border bg-card/60 px-4 py-3 text-center backdrop-blur">
      <div className="text-[10px] uppercase tracking-widest text-muted-foreground">{label}</div>
      <div className="mt-1 text-base font-semibold">{value}</div>
    </div>
  );
}

function MetricCard({
  icon,
  label,
  value,
  unit,
  hint,
  highlight,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  unit?: string;
  hint?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-2xl border bg-card p-6 transition-all ${
        highlight ? "border-primary/40" : "border-border"
      }`}
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      <div className="flex items-center justify-between">
        <div className="text-xs uppercase tracking-widest text-muted-foreground">{label}</div>
        <div
          className={`flex h-8 w-8 items-center justify-center rounded-lg ${
            highlight ? "text-primary-foreground" : "bg-accent text-accent-foreground"
          }`}
          style={highlight ? { backgroundImage: "var(--gradient-primary)" } : undefined}
        >
          {icon}
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className={`text-3xl font-semibold tracking-tight ${highlight ? "text-primary" : ""}`}>{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </div>
      {hint && <div className="mt-2 text-xs text-muted-foreground">{hint}</div>}
    </div>
  );
}

export default ResultsPage;