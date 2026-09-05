import { useMemo, useState } from "react";
import type { PluginSummary } from "../types/plugin";

export function PluginPicker({
  plugins,
  osHint,
  selected,
  onSelect,
}: {
  plugins: PluginSummary[];
  osHint: string | null;
  selected: string | null;
  onSelect: (name: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [showAllOs, setShowAllOs] = useState(false);

  const filterByOs = Boolean(osHint) && !showAllOs;

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return plugins
      .filter((p) => !filterByOs || !p.os || p.os === osHint)
      .filter((p) => !q || p.name.toLowerCase().includes(q) || p.description.toLowerCase().includes(q));
  }, [plugins, osHint, filterByOs, query]);

  return (
    <div className="plugin-picker">
      {osHint && (
        <p className="os-filter-note">
          Showing <strong>{osHint}</strong> plugins for this image.{" "}
          <button type="button" className="link-button" onClick={() => setShowAllOs((v) => !v)}>
            {showAllOs ? "Filter to detected OS" : "Show all OS plugins"}
          </button>
        </p>
      )}
      <input
        type="search"
        placeholder="Search plugins..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="plugin-picker-search"
      />
      <ul className="plugin-picker-list">
        {filtered.map((p) => (
          <li key={p.name}>
            <button
              type="button"
              className={p.name === selected ? "plugin-item selected" : "plugin-item"}
              onClick={() => onSelect(p.name)}
            >
              <span className="plugin-name">{p.name}</span>
              {p.os && <span className="plugin-os">{p.os}</span>}
              <span className="plugin-desc">{p.description}</span>
            </button>
          </li>
        ))}
        {filtered.length === 0 && <li className="plugin-empty">No plugins match.</li>}
      </ul>
    </div>
  );
}
