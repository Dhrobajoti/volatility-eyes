export type ImageStatus = "uploading" | "identifying" | "ready" | "error";

export interface VolImage {
  id: string;
  filename: string;
  size_bytes: number;
  sha256: string;
  os_hint: string | null;
  os_version: string | null;
  legacy_profile: string | null;
  status: ImageStatus;
  created_at: string;
}
