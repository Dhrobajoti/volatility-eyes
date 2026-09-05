import { get } from "./client";
import type { PluginSchema, PluginSummary } from "../types/plugin";

export function listPlugins(): Promise<PluginSummary[]> {
  return get<PluginSummary[]>("/api/plugins");
}

export function getPluginSchema(name: string): Promise<PluginSchema> {
  return get<PluginSchema>(`/api/plugins/${encodeURIComponent(name)}/schema`);
}
