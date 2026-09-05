from app.vol_service import get_plugin_schema, list_plugins
from app.vol_service.exceptions import PluginNotFoundError


def test_list_plugins_returns_many_plugins():
    plugins = list_plugins()
    assert len(plugins) > 100
    names = {p.name for p in plugins}
    assert "windows.pslist.PsList" in names
    assert "linux.pslist.PsList" in names


def test_pslist_schema_only_exposes_simple_fields():
    schema = get_plugin_schema("windows.pslist.PsList")
    field_names = {f.name for f in schema.fields}
    assert field_names == {"physical", "pid", "dump"}
    pid_field = next(f for f in schema.fields if f.name == "pid")
    assert pid_field.type == "array"
    assert pid_field.item_type == "integer"


def test_choice_requirement_maps_to_enum_field():
    schema = get_plugin_schema("mac.pslist.PsList")
    method_field = next(f for f in schema.fields if f.name == "pslist_method")
    assert method_field.type == "enum"
    assert "tasks" in method_field.choices


def test_every_discovered_plugin_produces_a_schema_without_error():
    for plugin in list_plugins():
        get_plugin_schema(plugin.name)  # must not raise


def test_unknown_plugin_raises_plugin_not_found_error():
    try:
        get_plugin_schema("does.not.Exist")
    except PluginNotFoundError:
        pass
    else:
        raise AssertionError("expected PluginNotFoundError")
