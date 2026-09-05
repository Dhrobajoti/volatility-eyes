import { useEffect, useState } from "react";
import { get, post } from "./client";
import type { PluginSummary } from "../types/plugin";
import type { VolImage } from "../types/image";

export function listLegacyPlugins(): Promise<PluginSummary[]> {
  return get<{ name: string; description: string }[]>("/api/legacy/plugins").then((rows) =>
    rows.map((r) => ({ name: r.name, description: r.description, os: "windows" })),
  );
}

export function identifyLegacyProfile(imageId: string): Promise<VolImage> {
  return post<VolImage>(`/api/legacy/images/${imageId}/identify`, {});
}

/**
 * Unlike Insights, the legacy service is on by default (see
 * docker-compose.yml) - but it's still a separate container that could be
 * down/removed, so the same reachability-gated pattern applies: hide the UI
 * cleanly rather than let it fail when clicked.
 */
export function useLegacyAvailable(): boolean | null {
  const [available, setAvailable] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    get<{ available: boolean }>("/api/legacy/health")
      .then((r) => !cancelled && setAvailable(r.available))
      .catch(() => !cancelled && setAvailable(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return available;
}
