import inspect

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.drop_source_columns import (
    DROP_SOURCE_COLUMNS,
    split_converter_params,
)
from DashAI.back.converters.scikit_learn.one_hot_encoder import OneHotEncoder
from DashAI.back.dependencies.config_builder import get_initial_components


def _builtin_converters():
    return [
        component
        for component in get_initial_components()
        if inspect.isclass(component)
        and issubclass(component, BaseConverter)
        and component.SCHEMA is not None
    ]


def test_every_add_converter_exposes_the_option_and_no_other_does():
    converters = _builtin_converters()
    assert converters
    for cls in converters:
        has_field = DROP_SOURCE_COLUMNS in cls.SCHEMA.model_fields
        assert has_field == (cls.COLUMN_OPERATION == "add"), cls.__name__


def test_the_option_defaults_to_off_and_is_the_last_form_field():
    schema = OneHotEncoder.get_schema()
    assert list(schema["properties"])[-1] == DROP_SOURCE_COLUMNS
    assert schema["properties"][DROP_SOURCE_COLUMNS]["placeholder"] is False


def test_split_converter_params_strips_the_flag_without_mutating():
    params = {"sparse": False, DROP_SOURCE_COLUMNS: True}
    clean, drop = split_converter_params(params)
    assert clean == {"sparse": False}
    assert drop is True
    assert DROP_SOURCE_COLUMNS in params
    assert split_converter_params(None) == ({}, False)
    assert split_converter_params({"a": 1}) == ({"a": 1}, False)


def test_params_saved_before_the_option_still_validate_as_off():
    properties = OneHotEncoder.get_schema()["properties"]
    saved = {
        name: field["placeholder"]
        for name, field in properties.items()
        if name != DROP_SOURCE_COLUMNS
    }
    validated = OneHotEncoder.SCHEMA.model_validate(saved)
    assert validated.drop_source_columns is False
