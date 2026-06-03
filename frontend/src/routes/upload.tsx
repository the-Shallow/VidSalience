// import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useNavigate } from "react-router-dom";
import { useRef, useState } from "react";
import { UploadCloud, FileVideo, Loader2, AlertCircle } from "lucide-react";
import { SiteHeader } from "@/components/SiteHeader";
import { Button } from "@/components/ui/button";
import { uploadVideo } from "@/lib/api";

const ACCEPTED = [".mp4", ".mov", ".avi", ".mkv"];
const ACCEPT_ATTR = "video/mp4,video/quicktime,video/x-msvideo,video/x-matroska,.mp4,.mov,.avi,.mkv";

// export const Route = createFileRoute("/upload")({
//   head: () => ({
//     meta: [
//       { title: "Upload Video — VidSalience" },
//       { name: "description", content: "Upload a video to compress with saliency-aware AI." },
//     ],
//   }),
//   component: UploadPage,
// });

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
  return `${(bytes / 1024 ** 3).toFixed(2)} GB`;
}

function hasValidExtension(name: string) {
  return ACCEPTED.some((ext) => name.toLowerCase().endsWith(ext));
}

function UploadPage() {
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pick(f: File | null | undefined) {
    setError(null);
    if (!f) return;
    if (!hasValidExtension(f.name)) {
      setError(`Unsupported file type. Accepted: ${ACCEPTED.join(", ")}`);
      return;
    }
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const res = await uploadVideo(file);
    //   navigate({ to: "/status/$jobId", params: { jobId: res.job_id } });
      navigate(`/status/${res.job_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setUploading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background">
      <SiteHeader />
      <main className="mx-auto max-w-3xl px-6 py-16">
        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Upload a video</h1>
          <p className="mt-2 text-muted-foreground">
            Drop in a video file to start a saliency-aware compression job. Accepted formats: {ACCEPTED.join(", ")}.
          </p>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            pick(e.dataTransfer.files?.[0]);
          }}
          onClick={() => inputRef.current?.click()}
          className={`group relative cursor-pointer rounded-2xl border-2 border-dashed bg-card p-12 text-center transition-all ${
            dragOver ? "border-primary bg-accent/40" : "border-border hover:border-primary/60"
          }`}
          style={{ boxShadow: "var(--shadow-card)" }}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT_ATTR}
            className="hidden"
            onChange={(e) => pick(e.target.files?.[0])}
          />
          <div
            className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl text-primary-foreground"
            style={{ backgroundImage: "var(--gradient-primary)" }}
          >
            <UploadCloud className="h-6 w-6" />
          </div>
          <p className="text-base font-medium">
            {dragOver ? "Drop to upload" : "Drag & drop your video, or click to browse"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            MP4, MOV, AVI, MKV
          </p>
        </div>

        {file && (
          <div className="mt-6 flex items-center gap-4 rounded-xl border border-border bg-card p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <FileVideo className="h-5 w-5" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-sm font-medium">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
            </div>
            <Button variant="ghost" size="sm" onClick={() => setFile(null)} disabled={uploading}>
              Remove
            </Button>
          </div>
        )}

        {error && (
          <div className="mt-6 flex items-start gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="mt-8 flex justify-end">
          <Button onClick={submit} disabled={!file || uploading} size="lg">
            {uploading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Uploading…
              </>
            ) : (
              <>Upload & Compress</>
            )}
          </Button>
        </div>
      </main>
    </div>
  );
}

export default UploadPage;