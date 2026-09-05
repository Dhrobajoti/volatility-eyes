import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getInsightSession } from "../api/insights";
import { MarkdownLite } from "../components/MarkdownLite";
import type { InsightSessionDetail } from "../types/insight";

const TERMINAL = new Set(["ready", "failed"]);

const STATUS_LABEL: Record<string, string> = {
  gathering: "Running baseline plugins...",
  summarizing: "Asking the model for a summary...",
  ready: "Ready",
  failed: "Failed",
};

// A per-job session (source_job_id set) never runs plugins itself - it only
// reads a job that's already completed - so "gathering" briefly means
// "queued, about to summarize", not "running baseline plugins".
const JOB_STATUS_LABEL: Record<string, string> = {
  ...STATUS_LABEL,
  gathering: "Preparing analysis...",
};

export function InsightSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<InsightSessionDetail | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    let interval: ReturnType<typeof setInterval> | null = null;

    const poll = () => {
      getInsightSession(sessionId).then((s) => {
        if (cancelled) return;
        setSession(s);
        if (TERMINAL.has(s.status) && interval) {
          clearInterval(interval);
          interval = null;
        }
      });
    };

    poll();
    interval = setInterval(poll, 2500);
    return () => {
      cancelled = true;
      if (interval) clearInterval(interval);
    };
  }, [sessionId]);

  if (!session) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h1>Insights — {session.image_filename ?? "(deleted image)"}</h1>
      <p className="job-meta">
        Session {session.id} — status: <strong>{session.status}</strong>
        {session.model_used && <> — model: {session.model_used}</>}
        {session.source_job_id && (
          <>
            {" "}
            — analyzing <Link to={`/jobs/${session.source_job_id}`}>job {session.source_job_id.slice(0, 8)}</Link>
          </>
        )}
      </p>

      {!TERMINAL.has(session.status) && (
        <p className="form-empty">
          {(session.source_job_id ? JOB_STATUS_LABEL : STATUS_LABEL)[session.status] ?? session.status}
        </p>
      )}

      {session.status === "failed" && (
        <div className="error-box">
          <strong>Failed:</strong> {session.error?.message ?? "Unknown error"}
        </div>
      )}

      {session.messages.map((m) => (
        <div key={m.id} className="insight-message">
          <p className="insight-disclaimer">
            AI-generated interpretation, not forensic fact — verify against the linked jobs.
          </p>
          <div className="insight-content">
            <MarkdownLite text={m.content} />
          </div>
          {m.referenced_job_ids && m.referenced_job_ids.length > 0 && (
            <p className="insight-sources">
              Based on:{" "}
              {m.referenced_job_ids.map((jobId, i) => (
                <span key={jobId}>
                  {i > 0 && ", "}
                  <Link to={`/jobs/${jobId}`}>job {jobId.slice(0, 8)}</Link>
                </span>
              ))}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}
