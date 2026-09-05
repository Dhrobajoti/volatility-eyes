import { useRef, useState } from "react";
import { uploadImage } from "../api/images";
import type { VolImage } from "../types/image";

// Files people commonly reach for by mistake when they actually want a VM's
// memory contents - none of these hold RAM data, so uploading them always
// wastes time (OS detection fails, nothing to analyze). Mapped to a specific
// explanation since "not a valid file" alone doesn't tell you what to do.
const KNOWN_NON_MEMORY_FILES: Record<string, string> = {
  nvram:
    "VMware's firmware/BIOS state file, not RAM contents. Suspend the VM (or take a snapshot with memory) and upload the .vmem file from the same folder instead.",
  vmx: "VMware's VM configuration file, not RAM contents. Upload the .vmem file from the same folder instead.",
  vmxf: "VMware's supplemental config file, not RAM contents. Upload the .vmem file from the same folder instead.",
  vmsd: "VMware's snapshot metadata file, not RAM contents. Upload the .vmem file from the same folder instead.",
  vmdk: "A virtual disk file (VM storage), not RAM contents. Upload the .vmem file from the same folder instead.",
  ova: "A packaged VM export, not a raw memory image.",
  ovf: "A packaged VM export, not a raw memory image.",
  log: "A log file, not a memory image.",
};

const SMALL_FILE_WARNING_BYTES = 10 * 1024 * 1024; // real memory images are practically always much bigger than this

function extensionOf(filename: string): string {
  const parts = filename.split(".");
  return parts.length > 1 ? parts[parts.length - 1].toLowerCase() : "";
}

export function ImageUploader({ onUploaded }: { onUploaded: (image: VolImage) => void }) {
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);

    const ext = extensionOf(file.name);
    const knownIssue = KNOWN_NON_MEMORY_FILES[ext];
    if (knownIssue) {
      setError(`"${file.name}" looks like a ${ext.toUpperCase()} file - ${knownIssue}`);
      if (inputRef.current) inputRef.current.value = "";
      return;
    }
    if (
      file.size < SMALL_FILE_WARNING_BYTES &&
      !confirm(
        `"${file.name}" is only ${(file.size / 1024).toFixed(0)} KB - real memory images are ` +
          "usually hundreds of MB or more. Upload it anyway?",
      )
    ) {
      if (inputRef.current) inputRef.current.value = "";
      return;
    }

    setProgress(0);
    try {
      const image = await uploadImage(file, setProgress);
      onUploaded(image);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setProgress(null);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="uploader">
      <label className="uploader-drop">
        <input
          ref={inputRef}
          type="file"
          accept=".raw,.vmem,.dmp,.mem,.img,.lime,.core,.vmss,.vmsn,.bin"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <span>Choose a memory image (.raw, .vmem, .dmp, .mem)</span>
      </label>
      {progress !== null && (
        <div className="progress-bar">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
          <span className="progress-bar-label">{progress.toFixed(0)}%</span>
        </div>
      )}
      {error && <p className="error-text">{error}</p>}
    </div>
  );
}
