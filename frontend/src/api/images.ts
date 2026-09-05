import { BASE_URL, del, get, post } from "./client";
import type { VolImage } from "../types/image";

export function listImages(): Promise<VolImage[]> {
  return get<VolImage[]>("/api/images");
}

export function deleteImage(id: string): Promise<void> {
  return del(`/api/images/${id}`);
}

export function identifyImage(id: string): Promise<VolImage> {
  return post<VolImage>(`/api/images/${id}/identify`, {});
}

export function uploadImage(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<VolImage> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/api/images`);
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress((e.loaded / e.total) * 100);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error(xhr.responseText || xhr.statusText));
      }
    };
    xhr.onerror = () => reject(new Error("Upload failed"));

    const formData = new FormData();
    formData.append("file", file);
    xhr.send(formData);
  });
}
