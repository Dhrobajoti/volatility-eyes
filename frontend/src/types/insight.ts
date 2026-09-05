export type InsightSessionStatus = "gathering" | "summarizing" | "ready" | "failed";
export type InsightRole = "user" | "assistant";

export interface InsightMessage {
  id: string;
  role: InsightRole;
  content: string;
  referenced_job_ids: string[] | null;
  created_at: string;
}

export interface InsightSession {
  id: string;
  image_id: string;
  image_filename: string | null;
  source_job_id: string | null;
  status: InsightSessionStatus;
  model_used: string | null;
  error: { message?: string } | null;
  created_at: string;
  updated_at: string;
}

export interface InsightSessionDetail extends InsightSession {
  messages: InsightMessage[];
}
