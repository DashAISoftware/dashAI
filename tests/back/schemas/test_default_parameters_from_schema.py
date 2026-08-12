from DashAI.back.core.schema_fields import (
    BaseSchema,
    default_parameters_from_schema,
    float_field,
    int_field,
    schema_field,
)


class _DummyModelSchema(BaseSchema):
    max_tokens: schema_field(
        int_field(ge=1),
        placeholder=100,
        description="Max tokens",
    )  # type: ignore
    temperature: schema_field(
        float_field(ge=0.0, le=1.0),
        placeholder=0.7,
        description="Temperature",
    )  # type: ignore


def test_default_parameters_from_schema_extracts_every_placeholder():
    defaults = default_parameters_from_schema(_DummyModelSchema)

    assert defaults == {"max_tokens": 100, "temperature": 0.7}


def test_default_parameters_from_schema_result_satisfies_the_schema():
    defaults = default_parameters_from_schema(_DummyModelSchema)

    # Would raise pydantic.ValidationError if any required field were missing.
    _DummyModelSchema.model_validate(defaults)
