"""Plugin settings, saved as non-default values in ``<plugins>/settings/<id>.json``."""

import json
import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional, Set, Type

from kink import di
from pydantic import ValidationError

from DashAI.back.core.schema_fields import SEARCH_DTYPE_KEY, BaseSchema
from DashAI.back.core.schema_fields.base_schema import replace_defs_in_schema
from DashAI.back.core.schema_fields.defaults import resolve_schema_defaults
from DashAI.back.core.schema_fields.utils import normalize_payload
from DashAI.back.plugins.disk.trash import retry_busy, write_json
from DashAI.back.plugins.errors import CodedError
from DashAI.back.plugins.loader import owner_of

SETTINGS_DIR = "settings"

logger = logging.getLogger(__name__)
# Requests run in threads and write_json reuses one temp file
_write_lock = threading.Lock()


class InvalidSettingsError(CodedError):
    """Values a save was asked for that do not validate."""

    code = "invalid_settings"


class BasePluginSettings(BaseSchema):
    """Base of plugin settings (placeholder is the default), ``load()`` on use."""

    # No TYPE, or the registry would take it as a component base class

    @classmethod
    def load(cls) -> "BasePluginSettings":
        """The settings in effect: the saved values over the defaults."""
        plugin_id = owner_of(cls.__module__)
        if plugin_id == "dashai":
            raise TypeError(f"{cls.__name__} is not a plugin's settings class")
        registry = di["component_registry"]
        saved = read(settings_file(di["plugin_storage"].root, plugin_id))
        return cls.model_validate(
            normalize_payload(
                {**defaults(cls, registry), **clean(cls, saved, registry)}
            )
        )


def settings_file(plugins_root: Path, plugin_id: str) -> Path:
    """Where a plugin's saved values live (``plugins_root``: ``~/.DashAI/plugins``)."""
    return Path(plugins_root) / SETTINGS_DIR / f"{plugin_id}.json"


def schema(cls: Type[BaseSchema], registry) -> Dict[str, Any]:
    """The form's JSON schema, naming components by id."""
    return registry.canonical_schema(
        replace_defs_in_schema(cls.model_json_schema()), owner_of(cls.__module__), cls
    )


def defaults(cls: Type[BaseSchema], registry) -> Dict[str, Any]:
    """Each field's placeholder, else pydantic's default."""
    return resolve_schema_defaults(
        schema(cls, registry), registry, only_placeholders=True
    )


def problem(cls: type, plugin_id: str, registry) -> Optional[str]:
    """Why a manifest's settings class is unusable, or None, checked at load."""
    if not (isinstance(cls, type) and issubclass(cls, BasePluginSettings)):
        return f"'{getattr(cls, '__name__', cls)}' must subclass BasePluginSettings"
    owner = owner_of(cls.__module__)
    if owner != plugin_id:
        # load() would read the owner's file.
        where = "dashAI" if owner == "dashai" else f"the plugin '{owner}'"
        return f"'{cls.__name__}' is defined in {where}, not in this plugin"
    try:
        properties = schema(cls, registry).get("properties", {})
    except Exception as error:  # noqa: BLE001 - the author's types
        return f"its schema cannot be generated: {type(error).__name__}: {error}"
    searched = sorted(k for k, p in properties.items() if SEARCH_DTYPE_KEY in p)
    if searched:
        return f"a setting can't be a search_space (a run's optimizer): {searched}"
    try:
        cls.model_validate(normalize_payload(defaults(cls, registry)))
    except ValidationError as error:
        return f"its default values (placeholders) are invalid: {error}"
    return None


def read(path: Path) -> Dict[str, Any]:
    """The saved values; {} if none, or if the file is not a JSON object."""
    try:
        # A save replacing the file right now may hold it busy.
        text = retry_busy(lambda: path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    try:
        data = json.loads(text)
    except ValueError as error:
        logger.warning("Ignoring unreadable plugin settings %s: %s", path, error)
        return {}
    if not isinstance(data, dict):
        logger.warning("Ignoring plugin settings %s: not a JSON object", path)
        return {}
    return data


def save(path: Path, values: Dict[str, Any]) -> None:
    with _write_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, values)


def clean(cls: Type[BaseSchema], saved: Dict[str, Any], registry) -> Dict[str, Any]:
    """Saved values the schema still accepts, all dropped if no field is named."""
    values = {key: value for key, value in saved.items() if key in cls.model_fields}
    base = defaults(cls, registry)
    while values:
        invalid = _invalid_keys(cls, values, base, registry)
        if invalid == set():
            return values
        logger.warning(
            "Ignoring invalid settings of %s: %s", cls.__name__, invalid or "all"
        )
        if invalid is None:
            return {}
        values = {key: value for key, value in values.items() if key not in invalid}
    return values


def changed(cls: Type[BaseSchema], values: Dict[str, Any], registry) -> Dict[str, Any]:
    """Non-default values to save, ``InvalidSettingsError`` if one is invalid."""
    values = {key: value for key, value in values.items() if key in cls.model_fields}
    base = defaults(cls, registry)
    invalid = _invalid_keys(cls, values, base, registry)
    if invalid != set():
        fields = sorted(invalid or [])
        raise InvalidSettingsError(
            f"Invalid settings: {fields or 'a rule'}", fields=fields
        )
    given = cls.model_validate(normalize_payload({**base, **values}))
    default = cls.model_validate(normalize_payload(base))
    return {
        key: value
        for key, value in values.items()
        if getattr(given, key) != getattr(default, key)
    }


def _invalid_keys(cls, values, base, registry) -> Optional[Set[str]]:
    """Keys of ``values`` failing over ``base``, None if the error names none."""
    merged = normalize_payload({**base, **values})
    # Pydantic only checks a component's shape. The plugin would look it up.
    missing = {
        key
        for key in values
        if isinstance(merged.get(key), dict)
        and {"component", "params"} <= merged[key].keys()
        and merged[key]["component"] not in registry
    }
    if missing:
        return missing
    try:
        cls.model_validate(merged)
    except ValidationError as error:
        named = {e["loc"][0] for e in error.errors() if e["loc"]} & values.keys()
        return named or None
    return set()
