import { useEffect, useState } from "react";
import { get, post } from "./client";
import type { InsightSession, InsightSessionDetail } from "../types/insight";

export function createInsightSession(imageId: string): Promise<InsightSession> {
  return post<InsightSession>("/api/insights/sessions", { image_id: imageId });
}

export function analyzeJob(jobId: string): Promise<InsightSession> {
  return post<InsightSession>(`/api/insights/jobs/${jobId}/analyze`, {});
}

export function listInsightSessions(imageId?: string): Promise<InsightSession[]> {
  const query = imageId ? `?image_id=${imageId}` : "";
  return get<InsightSession[]>(`/api/insights/sessions${query}`);
}

export function getInsightSession(id: string): Promise<InsightSessionDetail> {
  return get<InsightSessionDetail>(`/api/insights/sessions/${id}`);
}

/**
 * Whether the optional Insights feature is currently reachable - the
 * backend's health check reflects whether the `insights`/`ollama` Compose
 * profile was ever started, not just a hardcoded flag. Used to hide/disable
 * the Insights UI cleanly instead of it failing when clicked.
 */
export function useInsightsAvailable(): boolean | null {
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<{ available: boolean }>("/api/insights/health")
      .then((r) => !cancelled && setAvailable(r.available))
      .catch(() => !cancelled && setAvailable(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return available;
}
