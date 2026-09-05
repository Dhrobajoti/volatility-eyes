export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";
export type JobEngine = "v3" | "v2";

export interface JobError {
  type: "missing_params" | "invalid_plugin" | "internal";
  message?: string;
  fields?: { name: string; description: string }[];
}

export interface Job {
  id: string;
  image_id: string;
  image_filename: string | null;
  plugin_name: string;
  params: Record<string, unknown>;
  engine: JobEngine;
  status: JobStatus;
  progress_pct: number;
  progress_description: string | null;
  result_path: string | null;
  row_count: number | null;
  error: JobError | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface ResultNode {
  __children: ResultNode[];
  [column: string]: unknown;
}

export interface JobResult {
  columns: string[] | null;
  data: ResultNode[];
  raw_text: string | null;
}

export interface ProgressFrame {
  pct: number;
  description: string;
  terminal: boolean;
}
