import type { ResultNode } from "../types/job";

export function collectColumns(nodes: ResultNode[]): string[] {
  const cols = new Set<string>();
  for (const node of nodes) {
    for (const key of Object.keys(node)) {
      if (key !== "__children") cols.add(key);
    }
    if (node.__children) {
      for (const col of collectColumns(node.__children)) cols.add(col);
    }
  }
  return Array.from(cols);
}

export function formatCell(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

interface FlatRow {
  depth: number;
  values: string[];
}

function flatten(nodes: ResultNode[], columns: string[], depth: number, out: FlatRow[]): void {
  for (const node of nodes) {
    out.push({ depth, values: columns.map((col) => formatCell(node[col])) });
    if (node.__children?.length) {
      flatten(node.__children, columns, depth + 1, out);
    }
  }
}

/**
 * Renders a plugin result as an aligned, fixed-width text table - the same
 * general shape as volatility2/volatility3's own CLI text output. Tree
 * results are flattened with indentation on the first column rather than
 * nested, since plain text has no expand/collapse.
 */
export function buildTextReport(
  pluginName: string,
  jobId: string,
  columns: string[],
  data: ResultNode[],
): string {
  const rows: FlatRow[] = [];
  flatten(data, columns, 0, rows);

  const indented = rows.map((r) => {
    const values = [...r.values];
    values[0] = "  ".repeat(r.depth) + values[0];
    return values;
  });

  const widths = columns.map((col, i) =>
    Math.max(col.length, ...indented.map((r) => r[i]?.length ?? 0)),
  );

  const formatRow = (values: string[]) =>
    values.map((v, i) => v.padEnd(widths[i])).join("  ").trimEnd();

  const lines = [
    `Volatility Eyes - ${pluginName}`,
    `Job: ${jobId}`,
    `Exported: ${new Date().toISOString()}`,
    `Rows: ${rows.length}`,
    "",
    formatRow(columns),
    widths.map((w) => "-".repeat(w)).join("  "),
    ...indented.map(formatRow),
  ];

  return lines.join("\n");
}

export function downloadTextFile(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function exportJobAsText(
  jobId: string,
  pluginName: string,
  data: ResultNode[],
): void {
  const columns = collectColumns(data);
  const text = buildTextReport(pluginName, jobId, columns, data);
  const safePlugin = pluginName.replace(/[^a-z0-9.-]/gi, "_");
  downloadTextFile(`${safePlugin}_${jobId.slice(0, 8)}.txt`, text);
}
