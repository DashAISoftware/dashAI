"""Transformer encoders pooled into embeddings, tested with fake weights.

Nothing here downloads a checkpoint: a whitespace tokenizer and a deterministic
model stand in for ``AutoTokenizer``/``AutoModel``, so the pooling, the token
windows and the inherited ``fit``/``transform`` path run offline.
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import numpy as np
import pyarrow as pa
import pytest
import torch

from DashAI.back.converters.hugging_face.text_embedding import (
    TEXT_EMBEDDING_CONVERTERS,
    DistilBERTEmbedding,
    RoBERTaEmbedding,
    TextEmbeddingConverter,
)
from DashAI.back.converters.hugging_face.text_embedding.base import (
    pool_owner_vectors,
)
from DashAI.back.converters.hugging_face.text_embedding.transformer import (
    AGGREGATE,
    DEFAULT_MAX_LENGTH,
    MAX,
    MEAN,
    UNBOUNDED_TOKEN_LIMIT,
    LoadedTransformer,
    TransformerEmbeddingSchema,
    TransformerTextEmbedding,
    _max_length,
    pool_token_embeddings,
)
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dependencies.config_builder import get_initial_components
from DashAI.back.types.value_types import Float, Text

HIDDEN_SIZE = 4
TOKEN_LIMIT = 6
#: Two special tokens are reserved by the encoder, so a window holds the rest.
WINDOW_SIZE = TOKEN_LIMIT - 2


def _hidden_vector(token_id: int) -> np.ndarray:
    """Return the row the fake model emits for one token id.

    Parameters
    ----------
    token_id : int
        The token, zero for padding.

    Returns
    -------
    np.ndarray
        ``(HIDDEN_SIZE,)`` float32 vector; padding maps to zeros, so a pooled
        vector only matches when the attention mask was honoured.
    """
    return np.arange(1, HIDDEN_SIZE + 1, dtype=np.float32) * float(token_id)


class FakeTransformerTokenizer:
    """Split on whitespace and give every new word the next token id."""

    def __init__(self, model_max_length: int = TOKEN_LIMIT) -> None:
        """Start an empty vocabulary.

        Parameters
        ----------
        model_max_length : int, optional
            The limit a real tokenizer publishes, read when the model config
            carries none. Default ``TOKEN_LIMIT``.
        """
        self.model_max_length = model_max_length
        self._ids: Dict[str, int] = {}

    def _token_id(self, word: str) -> int:
        """Return the id of a word, adding it to the vocabulary if new."""
        if word not in self._ids:
            self._ids[word] = len(self._ids) + 1
        return self._ids[word]

    def _row(self, text: str, limit: Optional[int]) -> List[int]:
        """Return the token ids of ``text``, cut to ``limit`` when given."""
        words = (text or "").split()
        if limit is not None:
            words = words[:limit]
        return [self._token_id(word) for word in words]

    def __call__(
        self,
        texts: Any,
        add_special_tokens: bool = True,
        padding: bool = False,
        truncation: bool = False,
        max_length: Optional[int] = None,
        return_tensors: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Tokenize one text or a batch, as a real tokenizer does.

        Parameters
        ----------
        texts : str or list of str
            The text or texts to tokenize.
        add_special_tokens : bool
            Ignored; the fake adds none.
        padding : bool
            Pad a batch to its longest row.
        truncation : bool
            Cut every row to ``max_length``.
        max_length : int, optional
            The limit used when ``truncation`` is set.
        return_tensors : str, optional
            ``"pt"`` for torch tensors, anything else for nested lists.
        **kwargs
            Ignored.

        Returns
        -------
        dict
            ``input_ids`` and, for tensors, ``attention_mask``.
        """
        single = isinstance(texts, str)
        values = [texts] if single else list(texts)
        rows = [
            self._row(value, max_length if truncation else None) for value in values
        ]
        if return_tensors != "pt":
            return {"input_ids": rows[0] if single else rows}

        width = max(len(row) for row in rows)
        input_ids = torch.zeros((len(rows), width), dtype=torch.long)
        attention_mask = torch.zeros((len(rows), width), dtype=torch.long)
        for index, row in enumerate(rows):
            if not row:
                continue
            input_ids[index, : len(row)] = torch.tensor(row, dtype=torch.long)
            attention_mask[index, : len(row)] = 1
        return {"input_ids": input_ids, "attention_mask": attention_mask}

    def decode(self, ids: List[int], **kwargs: Any) -> str:
        """Join token ids back into the words they stand for.

        Parameters
        ----------
        ids : list of int
            Token ids produced by this tokenizer. Zero is padding and decodes
            to nothing.
        **kwargs
            Ignored.

        Returns
        -------
        str
            The words joined by single spaces.
        """
        words = {token_id: word for word, token_id in self._ids.items()}
        return " ".join(words[int(token_id)] for token_id in ids if int(token_id))


class FakeTransformerModel:
    """Emit ``id * [1..hidden]`` per token and log every forward call."""

    def __init__(
        self,
        hidden_size: int = HIDDEN_SIZE,
        max_position_embeddings: int = TOKEN_LIMIT,
    ) -> None:
        """Store the config the converter reads and an empty call log."""
        self.config = SimpleNamespace(
            hidden_size=hidden_size, max_position_embeddings=max_position_embeddings
        )
        self.calls: List[Dict[str, Any]] = []
        self.device: Optional[str] = None
        self.evaluated = False

    def to(self, device: str) -> "FakeTransformerModel":
        """Record the device the converter moved the model to."""
        self.device = device
        return self

    def eval(self) -> "FakeTransformerModel":
        """Record that the converter switched the model to evaluation."""
        self.evaluated = True
        return self

    def __call__(self, input_ids: torch.Tensor, **kwargs: Any) -> Any:
        """Return token vectors of shape ``(batch, tokens, hidden)``."""
        self.calls.append({"input_ids": input_ids.tolist()})
        rows = [
            [_hidden_vector(int(token)).tolist() for token in row]
            for row in input_ids.tolist()
        ]
        hidden = torch.tensor(rows, dtype=torch.float32)
        return SimpleNamespace(last_hidden_state=hidden)


def with_fake_transformer(
    converter: TransformerTextEmbedding,
    hidden_size: int = HIDDEN_SIZE,
    token_limit: int = TOKEN_LIMIT,
) -> FakeTransformerModel:
    """Point a converter at a fake loaded transformer instead of the Hub.

    Parameters
    ----------
    converter : TransformerTextEmbedding
        The converter to patch.
    hidden_size : int, optional
        Size of every emitted vector. Default ``HIDDEN_SIZE``.
    token_limit : int, optional
        Token limit of the fake tokenizer and model. Default ``TOKEN_LIMIT``.

    Returns
    -------
    FakeTransformerModel
        The model the converter now uses, with its forward calls logged.
    """
    model = FakeTransformerModel(hidden_size, token_limit)
    converter._pretrained = LoadedTransformer(
        tokenizer=FakeTransformerTokenizer(token_limit),
        model=model,
        max_length=token_limit,
    )
    return model


def _dataset(values: List[Optional[str]]) -> DashAIDataset:
    """Return a one text column dataset holding ``values``."""
    return DashAIDataset(
        pa.table({"review": pa.array(values, type=pa.string())}),
        types={"review": Text(arrow_type=pa.string())},
    )


def test_both_transformer_models_are_registered_dataset_only():
    registered = {
        component.__name__
        for component in get_initial_components()
        if isinstance(component, type) and issubclass(component, TextEmbeddingConverter)
    }

    for component in (DistilBERTEmbedding, RoBERTaEmbedding):
        assert component in TEXT_EMBEDDING_CONVERTERS
        assert issubclass(component, TransformerTextEmbedding)
        assert component.__name__ in registered
        assert component.SCHEMA is TransformerEmbeddingSchema
        assert component.REQUIRES_DOWNLOAD
        assert component.DOWNLOAD_SIZE_BYTES > 0
        metadata = component.get_metadata()
        assert metadata["data_kinds"] == ["dataset"]
        assert metadata["allowed_types"] == ["Text"]


def test_the_pooling_strategies_are_mean_and_max():
    assert TransformerTextEmbedding.POOLING_STRATEGIES == (MEAN, MAX)
    assert (MEAN, MAX) == ("mean", "max")
    assert DistilBERTEmbedding().params["pooling_strategy"] == MEAN


def test_an_unknown_pooling_strategy_is_rejected():
    with pytest.raises(ValueError, match="pooling"):
        RoBERTaEmbedding(pooling_strategy="cls")


def test_mean_pooling_ignores_padding():
    token_embeddings = np.array(
        [
            [[1.0, 1.0], [3.0, 3.0], [99.0, 99.0]],
            [[5.0, 5.0], [99.0, 99.0], [0.0, 0.0]],
        ],
        dtype=np.float32,
    )
    attention_mask = np.array([[1, 1, 0], [1, 0, 0]], dtype=np.int64)

    pooled = pool_token_embeddings(token_embeddings, attention_mask, MEAN)

    assert pooled.shape == (2, 2)
    assert np.allclose(pooled, [[2.0, 2.0], [5.0, 5.0]])


def test_max_pooling_ignores_padding():
    token_embeddings = np.array(
        [
            [[1.0, 3.0], [3.0, 1.0], [99.0, 99.0]],
            [[5.0, 5.0], [99.0, 99.0], [0.0, 0.0]],
            [[7.0, 7.0], [8.0, 8.0], [9.0, 9.0]],
        ],
        dtype=np.float32,
    )
    attention_mask = np.array([[1, 1, 0], [1, 0, 0], [0, 0, 0]], dtype=np.int64)

    pooled = pool_token_embeddings(token_embeddings, attention_mask, MAX)

    assert np.allclose(pooled, [[3.0, 3.0], [5.0, 5.0], [0.0, 0.0]])


def test_pooling_rejects_an_unknown_strategy():
    token_embeddings = np.zeros((1, 1, 2), dtype=np.float32)
    attention_mask = np.ones((1, 1), dtype=np.int64)

    with pytest.raises(ValueError, match="pooling"):
        pool_token_embeddings(token_embeddings, attention_mask, "cls")


def test_pool_owner_vectors_averages_windows_per_text():
    vectors = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]], dtype=np.float32)

    pooled = pool_owner_vectors(vectors, [0, 0, 1], 2)

    assert np.allclose(pooled, [[2.0, 3.0], [5.0, 6.0]])


def test_pool_owner_vectors_handles_no_texts():
    pooled = pool_owner_vectors(np.zeros((0, 3), dtype=np.float32), [], 0)

    assert pooled.shape == (0, 0)
    assert pooled.dtype == np.float32


def test_max_length_uses_the_smallest_advertised_limit():
    tokenizer = FakeTransformerTokenizer(model_max_length=5)
    model = FakeTransformerModel(max_position_embeddings=7)

    assert _max_length(tokenizer, model) == 5


def test_max_length_uses_the_config_when_the_tokenizer_is_unbounded():
    tokenizer = FakeTransformerTokenizer(model_max_length=UNBOUNDED_TOKEN_LIMIT)
    model = FakeTransformerModel(max_position_embeddings=7)

    assert _max_length(tokenizer, model) == 7


def test_max_length_uses_the_tokenizer_when_the_config_has_none():
    tokenizer = FakeTransformerTokenizer(model_max_length=5)
    model = FakeTransformerModel()
    model.config = SimpleNamespace(hidden_size=HIDDEN_SIZE)

    assert _max_length(tokenizer, model) == 5


def test_max_length_ignores_the_unbounded_sentinel():
    tokenizer = FakeTransformerTokenizer(model_max_length=TOKEN_LIMIT)
    model = FakeTransformerModel(max_position_embeddings=UNBOUNDED_TOKEN_LIMIT)

    assert _max_length(tokenizer, model) == TOKEN_LIMIT


def test_max_length_falls_back_when_both_sides_are_unbounded():
    tokenizer = FakeTransformerTokenizer(model_max_length=UNBOUNDED_TOKEN_LIMIT)
    model = FakeTransformerModel(max_position_embeddings=UNBOUNDED_TOKEN_LIMIT)

    assert _max_length(tokenizer, model) == DEFAULT_MAX_LENGTH


def test_load_pretrained_moves_and_evaluates_the_model(monkeypatch):
    import transformers

    tokenizer = FakeTransformerTokenizer(TOKEN_LIMIT)
    model = FakeTransformerModel()
    monkeypatch.setattr(
        transformers,
        "AutoTokenizer",
        SimpleNamespace(from_pretrained=lambda source: tokenizer),
    )
    monkeypatch.setattr(
        transformers,
        "AutoModel",
        SimpleNamespace(from_pretrained=lambda source: model),
    )
    converter = DistilBERTEmbedding()

    loaded = converter.load_pretrained("fake/repo")

    assert loaded.tokenizer is tokenizer
    assert loaded.model is model
    assert loaded.max_length == TOKEN_LIMIT
    assert model.device == converter.device
    assert model.evaluated


def test_encode_applies_max_pooling():
    converter = DistilBERTEmbedding(pooling_strategy=MAX, normalize=False)
    with_fake_transformer(converter)

    vectors = converter.encode(["a b"])

    assert np.allclose(vectors, [[2.0, 4.0, 6.0, 8.0]])


def test_encode_truncates_and_normalizes():
    converter = DistilBERTEmbedding(batch_size=2)
    model = with_fake_transformer(converter)
    long_text = " ".join(f"w{index}" for index in range(10))

    vectors = converter.encode([long_text, "short text"])

    assert vectors.shape == (2, HIDDEN_SIZE)
    assert vectors.dtype == np.float32
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    assert max(len(ids) for ids in model.calls[0]["input_ids"]) == TOKEN_LIMIT


def test_encode_ignores_the_padding_of_a_longer_neighbour():
    converter = DistilBERTEmbedding(batch_size=8, normalize=False)
    with_fake_transformer(converter)

    alone = converter.encode(["alpha beta"])
    padded = converter.encode(["alpha beta", "gamma delta epsilon zeta eta theta"])

    assert np.allclose(alone[0], padded[0])


def test_encode_of_no_text_is_an_empty_matrix():
    converter = RoBERTaEmbedding()
    with_fake_transformer(converter)

    vectors = converter.encode([])

    assert vectors.shape == (0, HIDDEN_SIZE)
    assert vectors.dtype == np.float32


def test_a_bare_string_is_rejected():
    converter = DistilBERTEmbedding()
    with_fake_transformer(converter)

    with pytest.raises(TypeError, match="list of strings"):
        converter.encode("hello world")


def test_invalid_construction_options_are_rejected():
    with pytest.raises(ValueError, match="batch_size"):
        DistilBERTEmbedding(batch_size=0)
    with pytest.raises(TypeError, match="batch_size"):
        DistilBERTEmbedding(batch_size="32")
    with pytest.raises(TypeError, match="normalize"):
        DistilBERTEmbedding(normalize="false")


def test_an_unknown_role_is_rejected():
    converter = DistilBERTEmbedding()
    with_fake_transformer(converter)

    with pytest.raises(ValueError, match="role"):
        converter.encode(["x"], role="document")


def test_aggregate_encodes_token_windows_and_averages_them():
    converter = RoBERTaEmbedding(overflow_strategy=AGGREGATE, batch_size=8)
    model = with_fake_transformer(converter)
    tokenizer = converter.pretrained().tokenizer
    text = " ".join(f"w{index}" for index in range(10))

    vectors = converter.encode([text, "short text"])

    assert vectors.shape == (2, HIDDEN_SIZE)
    assert np.isfinite(vectors).all()
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0)
    windows = [tokenizer.decode(ids) for ids in model.calls[0]["input_ids"]]
    assert windows == [
        " ".join(f"w{index}" for index in range(WINDOW_SIZE)),
        " ".join(f"w{index}" for index in range(WINDOW_SIZE, 2 * WINDOW_SIZE)),
        " ".join(f"w{index}" for index in range(2 * WINDOW_SIZE, 10)),
        "short text",
    ]
    window_means = np.array(
        [
            np.mean([_hidden_vector(token) for token in ids], axis=0)
            for ids in model.calls[0]["input_ids"][:-1]
        ]
    )
    expected = window_means.mean(axis=0)
    assert np.allclose(vectors[0], expected / np.linalg.norm(expected), atol=1e-6)


def test_fit_and_transform_replace_text_with_float_columns():
    converter = DistilBERTEmbedding()
    with_fake_transformer(converter)
    data = _dataset(["good movie", None, "a b c d e f g"])

    result = converter.fit(data).transform(data)

    assert result.column_names == [
        f"emb_review_{index}" for index in range(HIDDEN_SIZE)
    ]
    assert len(result) == 3
    assert all(isinstance(result.types[name], Float) for name in result.column_names)
    assert result.arrow_table.column("emb_review_0").type == pa.float32()
