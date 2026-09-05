import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listJobs, getJobResult } from "../api/jobs";
import { exportJobAsText, downloadTextFile } from "../utils/resultText";
import type { Job } from "../types/job";

export function JobsListPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [exportingId, setExportingId] = useState<string | null>(null);

  useEffect(() => {
    listJobs().then(setJobs);
  }, []);

  async function handleExport(job: Job) {
    setExportingId(job.id);
    try {
      const result = await getJobResult(job.id);
      if (job.engine === "v2") {
        downloadTextFile(`${job.plugin_name}_${job.id.slice(0, 8)}.txt`, result.raw_text ?? "");
      } else {
        exportJobAsText(job.id, job.plugin_name, result.data);
      }
    } finally {
      setExportingId(null);
    }
  }

  return (
    <div className="page">
      <h1>Analysis</h1>
      {jobs.length === 0 ? (
        <p className="form-empty">No jobs yet.</p>
      ) : (
        <div className="jobs-table-scroll">
          <table className="result-table">
            <thead>
              <tr>
                <th>Image</th>
                <th>Plugin</th>
                <th>Engine</th>
                <th>Status</th>
                <th>Rows</th>
                <th>Created</th>
                <th>Export</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id}>
                  <td>{job.image_filename ?? "(deleted image)"}</td>
                  <td>
                    <Link to={`/jobs/${job.id}`}>{job.plugin_name}</Link>
                  </td>
                  <td>{job.engine === "v2" ? "volatility2" : "volatility3"}</td>
                  <td>{job.status}</td>
                  <td>{job.row_count ?? "-"}</td>
                  <td>{new Date(job.created_at).toLocaleString()}</td>
                  <td>
                    {job.status === "completed" ? (
                      <button
                        type="button"
                        className="link-button"
                        disabled={exportingId === job.id}
                        onClick={() => handleExport(job)}
                      >
                        {exportingId === job.id ? "Exporting..." : "Export"}
                      </button>
                    ) : (
                      "-"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
