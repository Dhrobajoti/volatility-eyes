import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { downloadTextFile } from "../utils/resultText";
import { analyzeJob, useInsightsAvailable } from "../api/insights";
import { ApiError } from "../api/client";

/**
 * volatility2 output is plain text (see volatility2/README.md - no reliable
 * structured output across its plugin catalog), so this is a much simpler
 * sibling to ResultTree: line-based search instead of column-aware
 * filtering, and export is just the raw text as-is.
 */
export function LegacyResultView({
  jobId,
  pluginName,
  text,
}: {
  jobId: string;
  pluginName: string;
  text: string;
}) {
  const [query, setQuery] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const navigate = useNavigate();
  const insightsAvailable = useInsightsAvailable();

  const lines = useMemo(() => text.split("\n"), [text]);
  const filteredLines = useMemo(() => {
    if (!query.trim()) return lines;
    const q = query.toLowerCase();
    return lines.filter((line) => line.toLowerCase().includes(q));
  }, [lines, query]);

  async function handleInsights() {
    setAnalyzing(true);
    setAnalyzeError(null);
    try {
      const session = await analyzeJob(jobId);
      navigate(`/insights/${session.id}`);
    } catch (e) {
      setAnalyzeError(e instanceof ApiError ? String(e.detail) : "Failed to start Insights");
      setAnalyzing(false);
    }
  }

  return (
    <div>
      <div className="result-toolbar">
        <input
          type="search"
          placeholder="Search output..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="result-search"
        />
        <button
          type="button"
          className="export-button"
          onClick={() => downloadTextFile(`${pluginName}_${jobId.slice(0, 8)}.txt`, text)}
        >
          Export as Text
        </button>
        {insightsAvailable && (
          <button type="button" className="export-button" disabled={analyzing} onClick={handleInsights}>
            {analyzing ? "Starting..." : "Insights"}
          </button>
        )}
      </div>
      {analyzeError && <p className="error-box">{analyzeError}</p>}
      {query.trim() && (
        <p className="result-search-count">
          {filteredLines.length} of {lines.length} lines match
        </p>
      )}
      <pre className="legacy-output">{filteredLines.join("\n")}</pre>
    </div>
  );
}
