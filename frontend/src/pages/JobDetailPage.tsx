import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useJobProgress } from "../api/ws";
import { getJobResult, listJobFiles } from "../api/jobs";
import { BASE_URL } from "../api/client";
import { ProgressBar } from "../components/ProgressBar";
import { ResultTree } from "../components/ResultTree";
import { LegacyResultView } from "../components/LegacyResultView";
import type { JobResult } from "../types/job";

const TERMINAL = new Set(["completed", "failed", "cancelled"]);

export function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const { job, latestFrame } = useJobProgress(jobId);
  const [result, setResult] = useState<JobResult | null>(null);
  const [files, setFiles] = useState<string[]>([]);

  useEffect(() => {
    if (job?.status === "completed" && jobId) {
      getJobResult(jobId).then(setResult);
      listJobFiles(jobId).then(setFiles);
    }
  }, [job?.status, jobId]);

  if (!job) return <div className="page">Loading...</div>;

  return (
    <div className="page">
      <h1>{job.plugin_name}</h1>
      <p className="job-meta">
        Job {job.id} — status: <strong>{job.status}</strong>
        {job.engine === "v2" && <span className="engine-badge">volatility2</span>}
      </p>

      {!TERMINAL.has(job.status) && (
        <ProgressBar
          pct={latestFrame?.pct ?? job.progress_pct}
          label={latestFrame?.description ?? job.progress_description ?? undefined}
        />
      )}

      {job.status === "failed" && job.error && (
        <div className="error-box">
          <strong>Failed:</strong>{" "}
          {job.error.type === "missing_params" && job.error.fields
            ? `Missing required parameters: ${job.error.fields.map((f) => f.name).join(", ")}`
            : job.error.message}
        </div>
      )}

      {job.status === "completed" && result && job.engine === "v2" && (
        <LegacyResultView jobId={job.id} pluginName={job.plugin_name} text={result.raw_text ?? ""} />
      )}

      {job.status === "completed" && result && job.engine !== "v2" && (
        <>
          <p>{result.data.length} top-level rows</p>
          <ResultTree data={result.data} jobId={job.id} pluginName={job.plugin_name} />
        </>
      )}

      {files.length > 0 && (
        <div className="job-files">
          <h2>Extracted files</h2>
          <ul>
            {files.map((f) => (
              <li key={f}>
                <a href={`${BASE_URL}/api/jobs/${jobId}/files/${encodeURIComponent(f)}`}>{f}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
