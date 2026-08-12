import pytest

from DashAI.back.core.schema_fields import (
    BaseSchema,
    float_field,
    int_field,
    schema_field,
)
from DashAI.back.insights.providers import (
    InsightProviderError,
    LocalModelInsightProvider,
    build_provider,
)


class _DummyGenerativeModel:
    REQUIRES_DOWNLOAD = False
    init_count = 0
    last_kwargs = None
    last_messages = None

    def __init__(self, **kwargs):
        _DummyGenerativeModel.init_count += 1
        _DummyGenerativeModel.last_kwargs = kwargs

    def generate(self, messages):
        _DummyGenerativeModel.last_messages = messages
        return ["a local insight"]


class _NotDownloadedModel:
    REQUIRES_DOWNLOAD = True

    def __init__(self, **kwargs):
        pass

    def generate(self, messages):
        return ["should never be called"]

    @classmethod
    def is_downloaded(cls):
        return False


class _SchemaBackedModelSchema(BaseSchema):
    max_tokens: schema_field(int_field(ge=1), placeholder=100, description="Max tokens")  # type: ignore
    temperature: schema_field(
        float_field(ge=0.0, le=1.0), placeholder=0.7, description="Temperature"
    )  # type: ignore


class _SchemaBackedModel:
    """Mirrors GGUFTextGenerationModel: required fields, no Pydantic defaults
    (only display placeholders), so building it with no params fails unless
    those placeholders are filled in first."""

    REQUIRES_DOWNLOAD = False
    SCHEMA = _SchemaBackedModelSchema
    last_kwargs = None

    def __init__(self, **kwargs):
        self.SCHEMA.model_validate(kwargs)
        _SchemaBackedModel.last_kwargs = kwargs

    def generate(self, messages):
        return ["a local insight"]


FAKE_REGISTRY = {
    "DummyGenerativeModel": {"class": _DummyGenerativeModel},
    "NotDownloadedModel": {"class": _NotDownloadedModel},
    "SchemaBackedModel": {"class": _SchemaBackedModel},
}


@pytest.fixture(autouse=True)
def _reset_dummy_model_state():
    _DummyGenerativeModel.init_count = 0
    _DummyGenerativeModel.last_kwargs = None
    _DummyGenerativeModel.last_messages = None


def test_complete_forwards_messages_to_generate_and_returns_first_output():
    messages = [{"role": "user", "content": "hi"}]
    provider = LocalModelInsightProvider("DummyGenerativeModel", {}, FAKE_REGISTRY)

    result = provider.complete(messages)

    assert result == "a local insight"
    assert _DummyGenerativeModel.last_messages == messages


def test_generation_params_are_forwarded_to_the_model_constructor():
    provider = LocalModelInsightProvider(
        "DummyGenerativeModel", {"temperature": 0.2}, FAKE_REGISTRY
    )

    provider.complete([{"role": "user", "content": "hi"}])

    assert _DummyGenerativeModel.last_kwargs == {"temperature": 0.2}


def test_model_is_loaded_lazily_and_reused_across_calls():
    provider = LocalModelInsightProvider("DummyGenerativeModel", {}, FAKE_REGISTRY)

    provider.complete([{"role": "user", "content": "hi"}])
    provider.complete([{"role": "user", "content": "hi again"}])

    assert _DummyGenerativeModel.init_count == 1


def test_close_releases_the_loaded_model():
    provider = LocalModelInsightProvider("DummyGenerativeModel", {}, FAKE_REGISTRY)

    provider.complete([{"role": "user", "content": "hi"}])
    provider.close()
    provider.complete([{"role": "user", "content": "hi again"}])

    assert _DummyGenerativeModel.init_count == 2


def test_complete_raises_when_model_requires_download_and_is_missing():
    provider = LocalModelInsightProvider("NotDownloadedModel", {}, FAKE_REGISTRY)

    with pytest.raises(InsightProviderError):
        provider.complete([{"role": "user", "content": "hi"}])


def test_build_provider_returns_a_local_model_insight_provider():
    provider = build_provider(
        "local", {"model_name": "DummyGenerativeModel"}, FAKE_REGISTRY
    )

    assert isinstance(provider, LocalModelInsightProvider)
    assert provider.complete([{"role": "user", "content": "hi"}]) == "a local insight"


def test_build_provider_forwards_generation_params():
    build_provider(
        "local",
        {
            "model_name": "DummyGenerativeModel",
            "generation_params": {"temperature": 0.9},
        },
        FAKE_REGISTRY,
    ).complete([{"role": "user", "content": "hi"}])

    assert _DummyGenerativeModel.last_kwargs == {"temperature": 0.9}


def test_build_provider_raises_for_remote_kind_not_implemented_yet():
    with pytest.raises(InsightProviderError, match="not implemented"):
        build_provider("remote", {}, FAKE_REGISTRY)


def test_build_provider_raises_for_an_unknown_kind():
    with pytest.raises(InsightProviderError, match="Unknown"):
        build_provider("carrier-pigeon", {}, FAKE_REGISTRY)


def test_ensure_model_fills_missing_params_from_schema_placeholders():
    provider = LocalModelInsightProvider("SchemaBackedModel", {}, FAKE_REGISTRY)

    result = provider.complete([{"role": "user", "content": "hi"}])

    assert result == "a local insight"
    assert _SchemaBackedModel.last_kwargs == {"max_tokens": 100, "temperature": 0.7}


def test_ensure_model_lets_generation_params_override_schema_placeholders():
    provider = LocalModelInsightProvider(
        "SchemaBackedModel", {"temperature": 0.1}, FAKE_REGISTRY
    )

    provider.complete([{"role": "user", "content": "hi"}])

    assert _SchemaBackedModel.last_kwargs == {"max_tokens": 100, "temperature": 0.1}
