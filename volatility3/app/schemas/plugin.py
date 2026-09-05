from pydantic import BaseModel


class ParamFieldOut(BaseModel):
    name: str
    type: str
    required: bool
    description: str
    default: object | None = None
    item_type: str | None = None
    min_elements: int | None = None
    max_elements: int | None = None
    choices: list[str] | None = None


class PluginSummaryOut(BaseModel):
    name: str
    os: str | None
    description: str


class PluginSchemaOut(BaseModel):
    name: str
    os: str | None
    description: str
    fields: list[ParamFieldOut]
