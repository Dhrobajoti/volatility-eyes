import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listInsightSessions } from "../api/insights";
import type { InsightSession } from "../types/insight";

export function InsightsListPage() {
  const [sessions, setSessions] = useState<InsightSession[]>([]);

  useEffect(() => {
    listInsightSessions().then(setSessions);
  }, []);

  return (
    <div className="page">
      <h1>Insights</h1>
      {sessions.length === 0 ? (
        <p className="form-empty">
          No insight sessions yet — click "Insights" next to an image on the Images page.
        </p>
      ) : (
        <table className="result-table">
          <thead>
            <tr>
              <th>Image</th>
              <th>Status</th>
              <th>Model</th>
              <th>Started</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((s) => (
              <tr key={s.id}>
                <td>
                  <Link to={`/insights/${s.id}`}>{s.image_filename ?? "(deleted image)"}</Link>
                </td>
                <td>{s.status}</td>
                <td>{s.model_used ?? "-"}</td>
                <td>{new Date(s.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
