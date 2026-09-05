export function ProgressBar({ pct, label }: { pct: number; label?: string }) {
  const clamped = Math.max(0, Math.min(100, pct));
  return (
    <div className="progress-bar">
      <div className="progress-bar-fill" style={{ width: `${clamped}%` }} />
      <span className="progress-bar-label">
        {clamped.toFixed(0)}%{label ? ` — ${label}` : ""}
      </span>
    </div>
  );
}
