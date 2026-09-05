from fastapi import APIRouter, HTTPException

from .. import vol_service
from ..schemas.plugin import PluginSchemaOut, PluginSummaryOut

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginSummaryOut])
def list_plugins() -> list[PluginSummaryOut]:
    return [PluginSummaryOut(**p.__dict__) for p in vol_service.list_plugins()]


@router.get("/{plugin_name:path}/schema", response_model=PluginSchemaOut)
def get_plugin_schema(plugin_name: str) -> PluginSchemaOut:
    try:
        schema = vol_service.get_plugin_schema(plugin_name)
    except vol_service.PluginNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PluginSchemaOut(
        name=schema.name,
        os=schema.os,
        description=schema.description,
        fields=[f.__dict__ for f in schema.fields],
    )
