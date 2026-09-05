import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { listImages } from "../api/images";
import { getPluginSchema, listPlugins } from "../api/plugins";
import { listLegacyPlugins, useLegacyAvailable } from "../api/legacy";
import { createJob } from "../api/jobs";
import { ApiError } from "../api/client";
import { PluginPicker } from "../components/PluginPicker";
import { DynamicParamForm } from "../components/DynamicParamForm";
import type { VolImage } from "../types/image";
import type { JobEngine } from "../types/job";
import type { PluginSchema, PluginSummary } from "../types/plugin";

export function NewJobPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const legacyAvailable = useLegacyAvailable();

  const [images, setImages] = useState<VolImage[]>([]);
  const [imageId, setImageId] = useState(searchParams.get("image_id") ?? "");
  const [engine, setEngine] = useState<JobEngine>("v3");
  const [plugins, setPlugins] = useState<PluginSummary[]>([]);
  const [legacyPlugins, setLegacyPlugins] = useState<PluginSummary[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState<string | null>(null);
  const [schema, setSchema] = useState<PluginSchema | null>(null);
  const [params, setParams] = useState<Record<string, unknown>>({});
  const [paramsValid, setParamsValid] = useState(true);
  const [legacyExtraArgs, setLegacyExtraArgs] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listImages().then(setImages);
    listPlugins().then(setPlugins);
  }, []);

  useEffect(() => {
    if (legacyAvailable) listLegacyPlugins().then(setLegacyPlugins);
  }, [legacyAvailable]);

  useEffect(() => {
    setSelectedPlugin(null);
    setSchema(null);
    setParams({});
    setLegacyExtraArgs("");
  }, [engine, imageId]);

  useEffect(() => {
    if (!selectedPlugin || engine !== "v3") {
      setSchema(null);
      return;
    }
    getPluginSchema(selectedPlugin).then(setSchema);
  }, [selectedPlugin, engine]);

  const selectedImage = images.find((i) => i.id === imageId) ?? null;
  const canUseLegacy = legacyAvailable && !!selectedImage?.legacy_profile;

  async function handleSubmit() {
    if (!imageId || !selectedPlugin) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const jobParams =
        engine === "v2"
          ? { extra_args: legacyExtraArgs.trim() ? legacyExtraArgs.trim().split(/\s+/) : [] }
          : params;
      const job = await createJob(imageId, selectedPlugin, jobParams, engine);
      navigate(`/jobs/${job.id}`);
    } catch (e) {
      if (e instanceof ApiError) {
        const detail = e.detail as { fields?: { name: string; description: string }[] } | string;
        if (typeof detail === "object" && detail?.fields) {
          setSubmitError(
            "Missing required fields: " + detail.fields.map((f) => f.name).join(", "),
          );
        } else {
          setSubmitError(String(detail));
        }
      } else {
        setSubmitError("Failed to submit job");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <h1>Run a Plugin</h1>

      <div className="form-field">
        <label>Memory image</label>
        <select value={imageId} onChange={(e) => setImageId(e.target.value)}>
          <option value="">-- choose an image --</option>
          {images.map((img) => (
            <option key={img.id} value={img.id}>
              {img.filename}
            </option>
          ))}
        </select>
      </div>

      {imageId && canUseLegacy && (
        <div className="form-field">
          <label>Engine</label>
          <select value={engine} onChange={(e) => setEngine(e.target.value as JobEngine)}>
            <option value="v3">volatility3 (default)</option>
            <option value="v2">
              volatility2 legacy - profile {selectedImage!.legacy_profile}
            </option>
          </select>
        </div>
      )}

      {imageId && (
        <div className="two-column">
          <PluginPicker
            plugins={engine === "v2" ? legacyPlugins : plugins}
            osHint={engine === "v2" ? null : selectedImage?.os_hint ?? null}
            selected={selectedPlugin}
            onSelect={setSelectedPlugin}
          />
          <div className="plugin-detail">
            {engine === "v2" ? (
              selectedPlugin ? (
                <>
                  <h2>{selectedPlugin}</h2>
                  <p>{legacyPlugins.find((p) => p.name === selectedPlugin)?.description}</p>
                  <div className="param-field">
                    <label>Extra arguments (optional)</label>
                    <input
                      type="text"
                      placeholder={'e.g. -K "Microsoft\\Windows NT\\CurrentVersion"'}
                      value={legacyExtraArgs}
                      onChange={(e) => setLegacyExtraArgs(e.target.value)}
                    />
                    <p className="param-desc">
                      Raw volatility2 CLI flags, space-separated. Most plugins (pslist,
                      connscan, etc.) need none of these.
                    </p>
                  </div>
                  {submitError && <p className="error-text">{submitError}</p>}
                  <button type="button" disabled={submitting} onClick={handleSubmit}>
                    {submitting ? "Submitting..." : "Run"}
                  </button>
                </>
              ) : (
                <p className="form-empty">Select a plugin to run.</p>
              )
            ) : schema ? (
              <>
                <h2>{schema.name}</h2>
                <p>{schema.description}</p>
                <DynamicParamForm
                  schema={schema}
                  onChange={(p, valid) => {
                    setParams(p);
                    setParamsValid(valid);
                  }}
                />
                {submitError && <p className="error-text">{submitError}</p>}
                <button
                  type="button"
                  disabled={!paramsValid || submitting}
                  onClick={handleSubmit}
                >
                  {submitting ? "Submitting..." : "Run"}
                </button>
              </>
            ) : (
              <p className="form-empty">Select a plugin to configure its parameters.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
