export type FieldType = "integer" | "string" | "boolean" | "bytes" | "array" | "enum";

export interface ParamField {
  name: string;
  type: FieldType;
  required: boolean;
  description: string;
  default: unknown;
  item_type: FieldType | null;
  min_elements: number | null;
  max_elements: number | null;
  choices: string[] | null;
}

export interface PluginSummary {
  name: string;
  os: string | null;
  description: string;
}

export interface PluginSchema {
  name: string;
  os: string | null;
  description: string;
  fields: ParamField[];
}
