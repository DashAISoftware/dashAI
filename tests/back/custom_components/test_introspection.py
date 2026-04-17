import pytest

from DashAI.back.custom_components.introspection import (
    describe_base,
    get_supported_base_classes,
    resolve_base_class,
)


def test_supported_base_classes_includes_basemodel():
    rows = get_supported_base_classes()
    names = {r["name"] for r in rows}
    assert "BaseModel" in names
    base_model_entry = next(r for r in rows if r["name"] == "BaseModel")
    assert base_model_entry["enabled"] is True
    assert base_model_entry["type"] == "Model"


def test_resolve_disabled_base_raises():
    with pytest.raises(ValueError, match="not enabled"):
        resolve_base_class("BaseConverter")


def test_resolve_unknown_base_raises():
    with pytest.raises(ValueError, match="not supported"):
        resolve_base_class("NotARealBase")


def test_describe_basemodel_has_abstract_methods_with_docstrings():
    info = describe_base("BaseModel")
    names = {m["name"] for m in info["abstract_methods"]}
    assert {"save", "load", "train"}.issubset(names)
    for method in info["abstract_methods"]:
        assert method["signature"].startswith("(")
        assert isinstance(method["docstring"], str)


def test_describe_basemodel_provides_skeleton():
    info = describe_base("BaseModel")
    assert "class MyModel(BaseModel)" in info["skeleton"]
    assert "def save" in info["skeleton"]
    assert "def load" in info["skeleton"]
    assert "def train" in info["skeleton"]
