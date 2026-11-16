import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)

from DashAI.back.plugins.errors import CodedError

# Also its folder and package name, so lowercase, '-' only, no Windows device name
PLUGIN_ID = re.compile(r"^(?!(con|prn|aux|nul|com\d|lpt\d)$)[a-z0-9]+(-[a-z0-9]+)*$")
_CLASS_REF = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*:[A-Za-z_]\w*$")


class ManifestError(CodedError):
    """Raised when a plugin manifest is missing or invalid."""

    code = "invalid_manifest"


def _class_ref(value: str) -> str:
    if not _CLASS_REF.fullmatch(value):
        raise ValueError("class must be 'module:Class' (e.g. 'my_model:MyModel')")
    return value


def _web_url(value: str) -> str:
    """An absolute http(s) URL, safe to show as a link."""
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(
            f"must be an http(s) URL (e.g. 'https://github.com/me'), not {value!r}"
        )
    return value


def in_range(version: str, spec: str | None) -> bool:
    try:
        return not spec or Version(version) in SpecifierSet(spec, prereleases=True)
    except InvalidVersion:
        return False


def split_plugin_dependencies(data):
    if not isinstance(data, dict) or not isinstance(
        data.get("plugin_dependencies", []), list
    ):
        return data
    ids, specifiers = [], {}
    for item in data.get("plugin_dependencies", []):
        try:
            requirement = Requirement(item)
        except (InvalidRequirement, TypeError):
            requirement = None
        if (
            not requirement
            or requirement.extras
            or requirement.url
            or requirement.marker
        ):
            ids.append(item)
            continue
        ids.append(requirement.name)
        if requirement.specifier:
            specifiers[requirement.name] = str(requirement.specifier)
    return {**data, "plugin_dependencies": ids, "plugin_specifiers": specifiers}


class Component(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    class_ref: Annotated[str, AfterValidator(_class_ref)] = Field(alias="class")
    type: str

    @property
    def name(self) -> str:
        """Class name: the component's name in the registry."""
        return self.class_ref.split(":")[-1]


class Author(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = ""
    email: str = ""
    url: str = ""  # their page (e.g. GitHub profile), shown as a link

    @field_validator("url")
    @classmethod
    def _validate_url(cls, value: str) -> str:
        return _web_url(value) if value else value

    @model_validator(mode="after")
    def _require_name_or_email(self) -> "Author":
        if not self.name and not self.email:
            raise ValueError("each author must have at least a name or an email")
        return self


class PluginManifest(BaseModel):
    manifest_version: Literal["1"]
    id: str
    name: str = Field(pattern=r"\S")
    authors: list[Author] = Field(min_length=1)
    components: list[Component] = Field(min_length=1)
    min_app_version: str
    version: str

    project_urls: dict[str, str] = Field(default_factory=dict)
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    # Ids of other plugins it needs (``dependencies`` is pip's).
    plugin_dependencies: list[str] = Field(default_factory=list)
    plugin_specifiers: dict[str, str] = Field(default_factory=dict)
    # "module:Class" of its BasePluginSettings subclass, kept out of the registry
    settings: str | None = None

    _split_plugin_dependencies = model_validator(mode="before")(
        split_plugin_dependencies
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value: str) -> str:
        if not PLUGIN_ID.fullmatch(value):
            raise ValueError(
                "id must be lowercase letters and digits, separated by single '-' "
                "(e.g. 'my-plugin'), and not a Windows device name (con, nul...)"
            )
        return value

    @field_validator("settings")
    @classmethod
    def _validate_settings(cls, value: str | None) -> str | None:
        return value if value is None else _class_ref(value)

    @field_validator("project_urls")
    @classmethod
    def _validate_project_urls(cls, value: dict[str, str]) -> dict[str, str]:
        for url in value.values():
            _web_url(url)
        return value

    @field_validator("components")
    @classmethod
    def _unique_names(cls, value: list[Component]) -> list[Component]:
        # The registry is keyed by class name, so two would overwrite each other.
        names = [component.name for component in value]
        repeated = sorted({name for name in names if names.count(name) > 1})
        if repeated:
            raise ValueError(f"component class names must be unique: {repeated}")
        return value

    @field_validator("version", "min_app_version")
    @classmethod
    def _validate_semver(cls, value: str, info: ValidationInfo) -> str:
        """Ensure version and min_app_version are valid semantic versions."""
        try:
            Version(value)
        except InvalidVersion as error:
            raise ValueError(
                f"{info.field_name} must be a valid semantic version"
            ) from error
        return value

    @field_validator("dependencies")
    @classmethod
    def _validate_dependencies(cls, value: list[str]) -> list[str]:
        """Ensure each dependency is a valid requirement specifier."""
        for dependency in value:
            try:
                Requirement(dependency)
            except InvalidRequirement as error:
                raise ValueError(
                    f"invalid dependency specifier: {dependency!r}"
                ) from error
        return value

    @field_validator("plugin_dependencies")
    @classmethod
    def _validate_plugin_dependencies(
        cls, value: list[str], info: ValidationInfo
    ) -> list[str]:
        invalid = [i for i in value if not PLUGIN_ID.fullmatch(i)]
        if invalid:
            raise ValueError(f"invalid plugin ids: {invalid}")
        if len(set(value)) != len(value):
            raise ValueError("plugin_dependencies has repeated ids")
        if info.data.get("id") in value:
            raise ValueError("a plugin cannot depend on itself")
        return value

    @classmethod
    def from_dict(cls, data: dict) -> "PluginManifest":
        try:
            return cls.model_validate(data)
        except ValidationError as error:
            fields = sorted(
                {".".join(map(str, e["loc"])) or "manifest" for e in error.errors()}
            )
            if fields == ["id"] and isinstance(data, dict):
                raise ManifestError(
                    str(error), "invalid_id", id=str(data.get("id"))
                ) from error
            raise ManifestError(str(error), fields=fields) from error

    @classmethod
    def from_file(cls, path: str | Path) -> "PluginManifest":
        try:
            stat = os.stat(path)
        except OSError:
            return cls._read(path)
        return _from_file(str(path), stat.st_ino, stat.st_mtime_ns, stat.st_size)

    @classmethod
    def _read(cls, path: str | Path) -> "PluginManifest":
        try:
            # utf-8-sig also accepts a BOM.
            data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        except FileNotFoundError:
            raise
        except OSError as error:  # e.g. locked by an antivirus, unreadable for now
            raise ManifestError(
                f"manifest.json could not be read: {error}", fields=["manifest"]
            ) from error
        except (ValueError, RecursionError) as error:  # not UTF-8, or not JSON
            raise ManifestError(
                f"manifest.json is not UTF-8 JSON: {error}", fields=["manifest"]
            ) from error
        return cls.from_dict(data)


@lru_cache(maxsize=4096)
def _from_file(path: str, *stamp: int) -> PluginManifest:
    return PluginManifest._read(path)
