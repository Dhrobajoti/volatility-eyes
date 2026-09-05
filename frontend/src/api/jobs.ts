import { get, post } from "./client";
import type { Job, JobEngine, JobResult } from "../types/job";

export function createJob(
  imageId: string,
  pluginName: string,
  params: Record<string, unknown>,
  engine: JobEngine = "v3",
): Promise<Job> {
  return post<Job>("/api/jobs", { image_id: imageId, plugin_name: pluginName, params, engine });
}

export function listJobs(imageId?: string): Promise<Job[]> {
  const query = imageId ? `?image_id=${imageId}` : "";
  return get<Job[]>(`/api/jobs${query}`);
}

export function getJob(id: string): Promise<Job> {
  return get<Job>(`/api/jobs/${id}`);
}

export function getJobResult(id: string): Promise<JobResult> {
  return get<JobResult>(`/api/jobs/${id}/result`);
}

export function listJobFiles(id: string): Promise<string[]> {
  return get<string[]>(`/api/jobs/${id}/files`);
}
