import { useEffect, useState } from "react";
import type { ParamField, PluginSchema } from "../types/plugin";

type FormValues = Record<string, unknown>;

function coerceScalar(itemType: ParamField["item_type"], raw: string): unknown {
  if (itemType === "integer") return Number(raw); // Number() natively parses "0x..." hex strings
  return raw;
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: ParamField;
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  switch (field.type) {
    case "boolean":
      return (
        <input
          type="checkbox"
          checked={Boolean(value)}
          onChange={(e) => onChange(e.target.checked)}
        />
      );
    case "enum":
      return (
        <select value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">-- select --</option>
          {field.choices?.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      );
    case "array": {
      const text = Array.isArray(value) ? (value as unknown[]).join(", ") : "";
      return (
        <input
          type="text"
          placeholder={`comma-separated ${field.item_type ?? "values"} (e.g. ${
            field.item_type === "integer" ? "4, 0x1a4" : "a, b, c"
          })`}
          defaultValue={text}
          onChange={(e) => {
            const raw = e.target.value;
            if (!raw.trim()) {
              onChange(null);
              return;
            }
            const items = raw
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean)
              .map((s) => coerceScalar(field.item_type, s));
            onChange(items);
          }}
        />
      );
    }
    case "integer":
      return (
        <input
          type="text"
          placeholder="decimal or 0x hex"
          defaultValue={value === null || value === undefined ? "" : String(value)}
          onChange={(e) => {
            const raw = e.target.value.trim();
            onChange(raw === "" ? null : Number(raw));
          }}
        />
      );
    default:
      return (
        <input
          type="text"
          defaultValue={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value || null)}
        />
      );
  }
}

export function DynamicParamForm({
  schema,
  onChange,
}: {
  schema: PluginSchema;
  onChange: (params: FormValues, valid: boolean) => void;
}) {
  const [values, setValues] = useState<FormValues>({});

  useEffect(() => {
    setValues({});
  }, [schema.name]);

  useEffect(() => {
    const valid = schema.fields
      .filter((f) => f.required)
      .every((f) => values[f.name] !== undefined && values[f.name] !== null && values[f.name] !== "");
    onChange(values, valid);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values, schema.name]);

  if (schema.fields.length === 0) {
    return <p className="form-empty">This plugin takes no extra parameters.</p>;
  }

  return (
    <div className="param-form">
      {schema.fields.map((field) => (
        <div key={field.name} className="param-field">
          <label>
            {field.name}
            {field.required && <span className="required-mark">*</span>}
          </label>
          <FieldInput
            field={field}
            value={values[field.name]}
            onChange={(v) => setValues((prev) => ({ ...prev, [field.name]: v }))}
          />
          <p className="param-desc">{field.description}</p>
        </div>
      ))}
    </div>
  );
}
