const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "";
console.log("Using API base URL:", BASE_URL);
export type JobStatus = "UPLOADED" | "QUEUED" | "PROCESSING" | "COMPLETED" | "FAILED";

export interface Job {
  job_id: string;
  original_filename: string;
  input_object_key: string;
  output_object_key: string | null;
  status: JobStatus;
  error_message: string | null;
  metrics: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface UploadResponse {
  message: string;
  job_id: string;
  status: JobStatus;
  input_object_key: string;
  job: Partial<Job>;
}

export interface ResultMetrics {
  average_psnr: number;
  average_ssim: number;
  average_saliency_weighted_psnr: number;
  original_size_mb: number;
  compressed_size_mb: number;
  compressed_bitrate_kbps: number;
}

export interface JobResult {
  job_id: string;
  status: "COMPLETED";
  original_filename: string;
  input_object_key: string;
  output_object_key: string;
  download_url: string;
  metrics: ResultMetrics;
}

function url(path: string) {
  return `${BASE_URL}${path}`;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const data = await res.json();
      detail = data?.detail || data?.message || JSON.stringify(data);
    } catch {
      detail = await res.text();
    }
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export async function uploadVideo(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(url("/api/videos/upload"), {
    method: "POST",
    body: form,
  });
  return handle<UploadResponse>(res);
}

export async function getJob(jobId: string): Promise<Job> {
  const res = await fetch(url(`/api/videos/${jobId}`));
  return handle<Job>(res);
}

export async function getResults(jobId: string): Promise<JobResult> {
  const res = await fetch(url(`/api/videos/${jobId}`));
  return handle<JobResult>(res);
}

export const API_BASE_URL = BASE_URL;