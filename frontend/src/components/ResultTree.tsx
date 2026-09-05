import { Fragment, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ResultNode } from "../types/job";
import { collectColumns, formatCell, exportJobAsText } from "../utils/resultText";
import { analyzeJob, useInsightsAvailable } from "../api/insights";
import { ApiError } from "../api/client";

function hasAnyChildren(nodes: ResultNode[]): boolean {
  return nodes.some((n) => (n.__children?.length ?? 0) > 0 || hasAnyChildren(n.__children ?? []));
}

function nodeMatches(node: ResultNode, columns: string[], query: string): boolean {
  return columns.some((col) => formatCell(node[col]).toLowerCase().includes(query));
}

/** Keeps a node if it matches, or if any descendant matches (drilling down to
 * just the matching descendants in that case) - so a search doesn't just hide
 * a whole branch because the match is a few levels deep. */
function filterNodes(nodes: ResultNode[], columns: string[], query: string): ResultNode[] {
  if (!query) return nodes;
  const result: ResultNode[] = [];
  for (const node of nodes) {
    if (nodeMatches(node, columns, query)) {
      result.push(node);
      continue;
    }
    const filteredChildren = filterNodes(node.__children ?? [], columns, query);
    if (filteredChildren.length > 0) {
      result.push({ ...node, __children: filteredChildren });
    }
  }
  return result;
}

function countNodes(nodes: ResultNode[]): number {
  return nodes.reduce((sum, n) => sum + 1 + countNodes(n.__children ?? []), 0);
}

function TreeRows({
  nodes,
  columns,
  depth,
  keyPrefix,
}: {
  nodes: ResultNode[];
  columns: string[];
  depth: number;
  keyPrefix: string;
}) {
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());

  return (
    <>
      {nodes.map((node, i) => {
        const rowKey = `${keyPrefix}-${i}`;
        const children = node.__children ?? [];
        const isCollapsed = collapsed.has(i);
        return (
          <Fragment key={rowKey}>
            <tr>
              {columns.map((col, colIdx) => (
                <td key={col} style={colIdx === 0 ? { paddingLeft: depth * 20 } : undefined}>
                  {colIdx === 0 && children.length > 0 && (
                    <button
                      type="button"
                      className="tree-toggle"
                      onClick={() =>
                        setCollapsed((prev) => {
                          const next = new Set(prev);
                          if (next.has(i)) next.delete(i);
                          else next.add(i);
                          return next;
                        })
                      }
                    >
                      {isCollapsed ? "▶" : "▼"}
                    </button>
                  )}
                  {formatCell(node[col])}
                </td>
              ))}
            </tr>
            {!isCollapsed && children.length > 0 && (
              <TreeRows nodes={children} columns={columns} depth={depth + 1} keyPrefix={rowKey} />
            )}
          </Fragment>
        );
      })}
    </>
  );
}

export function ResultTree({
  data,
  jobId,
  pluginName,
}: {
  data: ResultNode[];
  jobId: string;
  pluginName: string;
}) {
  const [query, setQuery] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const navigate = useNavigate();
  const insightsAvailable = useInsightsAvailable();
  const columns = useMemo(() => collectColumns(data), [data]);
  const treeMode = useMemo(() => hasAnyChildren(data), [data]);

  const filtered = useMemo(
    () => filterNodes(data, columns, query.trim().toLowerCase()),
    [data, columns, query],
  );

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

  if (data.length === 0) {
    return <p className="form-empty">No rows returned.</p>;
  }

  return (
    <div>
      <div className="result-toolbar">
        <input
          type="search"
          placeholder="Search all columns..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="result-search"
        />
        <button
          type="button"
          className="export-button"
          onClick={() => exportJobAsText(jobId, pluginName, filtered)}
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
          {countNodes(filtered)} of {countNodes(data)} rows match
        </p>
      )}
      {filtered.length === 0 ? (
        <p className="form-empty">No rows match "{query}".</p>
      ) : (
        <div className="result-table-wrap">
          <table className="result-table">
            <thead>
              <tr>
                {columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <TreeRows nodes={filtered} columns={columns} depth={treeMode ? 0 : 0} keyPrefix="root" />
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
