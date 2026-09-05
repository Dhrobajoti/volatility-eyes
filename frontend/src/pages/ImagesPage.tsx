import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteImage, identifyImage, listImages } from "../api/images";
import { createInsightSession, useInsightsAvailable } from "../api/insights";
import { identifyLegacyProfile, useLegacyAvailable } from "../api/legacy";
import { ApiError } from "../api/client";
import { ImageUploader } from "../components/ImageUploader";
import { EyeMark } from "../components/EyeMark";
import type { VolImage } from "../types/image";

function formatBytes(bytes: number): string {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit++;
  }
  return `${value.toFixed(1)} ${units[unit]}`;
}

export function ImagesPage() {
  const [images, setImages] = useState<VolImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionError, setActionError] = useState<string | null>(null);
  const [startingInsightFor, setStartingInsightFor] = useState<string | null>(null);
  const [identifyingLegacyFor, setIdentifyingLegacyFor] = useState<string | null>(null);
  const insightsAvailable = useInsightsAvailable();
  const legacyAvailable = useLegacyAvailable();
  const navigate = useNavigate();

  async function detectLegacyProfile(img: VolImage) {
    setIdentifyingLegacyFor(img.id);
    setActionError(null);
    try {
      await identifyLegacyProfile(img.id);
      refresh();
    } catch (e) {
      setActionError(e instanceof ApiError ? String(e.detail) : "Failed to detect legacy profile");
    } finally {
      setIdentifyingLegacyFor(null);
    }
  }

  async function startInsights(img: VolImage) {
    setStartingInsightFor(img.id);
    try {
      const session = await createInsightSession(img.id);
      navigate(`/insights/${session.id}`);
    } catch (e) {
      setActionError(e instanceof ApiError ? String(e.detail) : "Failed to start Insights");
    } finally {
      setStartingInsightFor(null);
    }
  }

  function refresh() {
    setLoading(true);
    listImages()
      .then(setImages)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  // Poll while any image is still being OS-identified, so the "OS" column
  // fills in without the user needing to manually reload.
  useEffect(() => {
    if (!images.some((img) => img.status === "identifying")) return;
    const interval = setInterval(() => {
      listImages().then(setImages);
    }, 2000);
    return () => clearInterval(interval);
  }, [images]);

  return (
    <div className="page">
      <div className="page-hero">
        <div className="page-hero-mark">
          <EyeMark size={32} />
        </div>
        <div>
          <h1>Memory Images</h1>
          <p className="page-hero-subtitle">
            Upload a memory capture, then analyze it with volatility3 or the legacy volatility2 engine.
          </p>
        </div>
      </div>
      <ImageUploader onUploaded={() => refresh()} />
      {actionError && <p className="error-text">{actionError}</p>}

      {loading ? (
        <p>Loading...</p>
      ) : images.length === 0 ? (
        <p className="form-empty">No images uploaded yet.</p>
      ) : (
        <table className="result-table">
          <thead>
            <tr>
              <th>Filename</th>
              <th>Size</th>
              <th>OS</th>
              <th>Version</th>
              {legacyAvailable && <th>Legacy Profile</th>}
              <th>Status</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {images.map((img) => (
              <tr key={img.id}>
                <td>{img.filename}</td>
                <td>{formatBytes(img.size_bytes)}</td>
                <td>
                  {img.os_hint ??
                    (img.status === "identifying" ? (
                      "detecting..."
                    ) : (
                      <>
                        unknown{" "}
                        <button
                          type="button"
                          className="link-button"
                          onClick={async () => {
                            await identifyImage(img.id);
                            refresh();
                          }}
                        >
                          identify
                        </button>
                      </>
                    ))}
                </td>
                <td>{img.os_version ?? (img.status === "identifying" && img.os_hint === "windows" ? "detecting..." : "-")}</td>
                {legacyAvailable && (
                  <td>
                    {img.legacy_profile ?? (
                      <button
                        type="button"
                        className="link-button"
                        disabled={identifyingLegacyFor === img.id}
                        onClick={() => detectLegacyProfile(img)}
                      >
                        {identifyingLegacyFor === img.id ? "Detecting..." : "detect"}
                      </button>
                    )}
                  </td>
                )}
                <td>{img.status}</td>
                <td>{new Date(img.created_at).toLocaleString()}</td>
                <td className="row-actions">
                  <Link to={`/jobs/new?image_id=${img.id}`}>Analyze</Link>
                  {insightsAvailable && (
                    <button
                      type="button"
                      className="link-button"
                      disabled={startingInsightFor === img.id}
                      onClick={() => startInsights(img)}
                    >
                      {startingInsightFor === img.id ? "Starting..." : "Insights"}
                    </button>
                  )}
                  <button
                    type="button"
                    className="link-button danger"
                    onClick={async () => {
                      if (!confirm(`Delete ${img.filename}?`)) return;
                      setActionError(null);
                      try {
                        await deleteImage(img.id);
                        refresh();
                      } catch (e) {
                        setActionError(
                          e instanceof ApiError ? String(e.detail) : "Failed to delete image",
                        );
                      }
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
