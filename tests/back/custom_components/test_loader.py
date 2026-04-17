import sys

import pytest

from DashAI.back.custom_components.loader import (
    MODULE_PREFIX,
    load_user_class,
    unload_user_module,
)

VALID_SOURCE = """
class Foo:
    value = 1
"""


SCHEMA_MODEL_SOURCE = """
from DashAI.back.core.schema_fields import (
    BaseSchema,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel


class SchemaProbeSchema(BaseSchema):
    count: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(en="Count"),
        alias=MultilingualString(en="Count"),
    )  # type: ignore


class SchemaProbeModel(BaseModel):
    SCHEMA = SchemaProbeSchema

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self
"""


def test_load_user_class_returns_class():
    cls = load_user_class(VALID_SOURCE, "Foo")
    assert cls.__name__ == "Foo"
    assert cls.value == 1


def test_load_user_class_missing_symbol():
    with pytest.raises(KeyError):
        load_user_class(VALID_SOURCE, "DoesNotExist")


def test_load_user_class_syntax_error():
    with pytest.raises(SyntaxError):
        load_user_class("class Broken(:\n    pass", "Broken")


def test_load_user_class_not_a_class():
    with pytest.raises(TypeError):
        load_user_class("Foo = 42", "Foo")


def test_loaded_module_is_registered_in_sys_modules():
    try:
        load_user_class(VALID_SOURCE, "Foo")
        assert f"{MODULE_PREFIX}Foo" in sys.modules
    finally:
        unload_user_module("Foo")
    assert f"{MODULE_PREFIX}Foo" not in sys.modules


def test_load_user_class_rebuilds_pydantic_schema():
    """Schema-carrying class must resolve fields to generate JSON schema."""
    try:
        cls = load_user_class(SCHEMA_MODEL_SOURCE, "SchemaProbeModel")
        # This is exactly what ComponentRegistry does during registration;
        # it must not raise PydanticUserError("not fully defined").
        schema = cls.get_schema()
        assert "count" in schema["properties"]
    finally:
        unload_user_module("SchemaProbeModel")
