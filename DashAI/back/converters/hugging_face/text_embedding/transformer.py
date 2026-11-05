"""Embeddings from a plain transformer encoder, pooled by mean or max.

``sentence_transformer.py`` wraps checkpoints that already know how to turn a
text into one vector. This module covers the other case: an encoder such as
DistilBERT or RoBERTa that only returns token vectors, which are pooled here
with the strategy the user picks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

import numpy as np

from DashAI.back.converters.hugging_face.pretrained_tool import batches
from DashAI.back.converters.hugging_face.text_embedding.base import (
    AGGREGATE,
    NORMALIZATION_EPSILON,
    TextEmbeddingConverter,
    TextEmbeddingSchema,
    l2_normalize,
    pool_owner_vectors,
    same_label,
    text_values,
    token_windows,
)
from DashAI.back.converters.hugging_face.text_embedding_roles import (
    PASSAGE,
    ROLES,
)
from DashAI.back.core.schema_fields import enum_field, schema_field
from DashAI.back.core.utils import MultilingualString

MEAN = "mean"
MAX = "max"
POOLING_STRATEGIES = (MEAN, MAX)
DEFAULT_POOLING_STRATEGY = MEAN

#: Config attribute naming the longest sequence an encoder accepts.
MAX_LENGTH_ATTRIBUTE = "max_position_embeddings"
#: Used only when neither the config nor the tokenizer publishes a limit.
DEFAULT_MAX_LENGTH = 512
#: Hugging Face uses a huge sentinel for "this side publishes no limit".
UNBOUNDED_TOKEN_LIMIT = 10**6
#: Stands in for padding under max pooling, where a masked value must lose.
PADDING_SENTINEL = np.finfo(np.float32).min


class TransformerEmbeddingSchema(TextEmbeddingSchema):
    """Options of an embedding built on a plain transformer encoder."""

    pooling_strategy: schema_field(
        enum_field(list(POOLING_STRATEGIES)),
        placeholder=DEFAULT_POOLING_STRATEGY,
        description=MultilingualString(
            en="How token vectors are merged into one vector: mean averages "
            "them, max keeps the highest value of every dimension. Mean is "
            "the usual choice.",
            es="Cómo se combinan los vectores de tokens en uno solo: mean los "
            "promedia, max conserva el valor más alto de cada dimensión. Mean "
            "es la opción habitual.",
            pt="Como os vetores de tokens se combinam em um só: mean faz a "
            "média, max mantém o maior valor de cada dimensão. Mean é a "
            "escolha usual.",
            de="Wie Token-Vektoren zu einem Vektor zusammengefasst werden: "
            "mean mittelt sie, max behält den höchsten Wert je Dimension. "
            "Üblich ist mean.",
            zh="如何把 token 向量合并为一个向量：mean 取平均，max 保留每一维的"
            "最大值。通常选择 mean。",
        ),
        alias=MultilingualString(
            en="Pooling",
            es="Agrupación",
            pt="Agrupamento",
            de="Pooling",
            zh="池化",
        ),
    )  # type: ignore


@dataclass(frozen=True)
class LoadedTransformer:
    """A tokenizer and its encoder, ready to run together.

    Attributes
    ----------
    tokenizer : Any
        The Hugging Face tokenizer.
    model : Any
        The encoder, already on the converter's device.
    max_length : int
        Longest token sequence the encoder accepts.
    """

    tokenizer: Any
    model: Any
    max_length: int


@dataclass(frozen=True)
class _WindowSource:
    """The two attributes :func:`token_windows` reads from a model."""

    tokenizer: Any
    max_seq_length: int


def pool_token_embeddings(
    token_embeddings: np.ndarray,
    attention_mask: np.ndarray,
    strategy: str,
) -> np.ndarray:
    """Merge token vectors into one vector per text.

    Parameters
    ----------
    token_embeddings : np.ndarray
        ``(batch, tokens, dim)`` hidden states of the encoder.
    attention_mask : np.ndarray
        ``(batch, tokens)`` mask, one for a real token and zero for padding.
    strategy : str
        ``"mean"`` or ``"max"``.

    Returns
    -------
    np.ndarray
        ``(batch, dim)`` float32 vectors, with the padding excluded. A row
        with no real token pools to zeros.

    Raises
    ------
    ValueError
        If ``strategy`` is not a known pooling strategy.
    """
    values = np.asarray(token_embeddings, dtype=np.float32)
    mask = np.asarray(attention_mask, dtype=np.float32)[..., np.newaxis]
    if strategy == MEAN:
        totals = np.sum(values * mask, axis=1)
        counts = np.clip(np.sum(mask, axis=1), NORMALIZATION_EPSILON, None)
        return (totals / counts).astype(np.float32)
    if strategy == MAX:
        masked = np.where(mask > 0, values, PADDING_SENTINEL)
        pooled = np.max(masked, axis=1)
        # A text with no tokens at all would otherwise keep the sentinel,
        # which is a number but not a meaning: pool it to zeros like mean does.
        empty = np.sum(mask, axis=1) == 0
        return np.where(empty, 0.0, pooled).astype(np.float32)
    raise ValueError(
        f"Unknown pooling strategy '{strategy}', expected one of {POOLING_STRATEGIES}."
    )


def _hidden_size(model: Any) -> int:
    """Return the width of the vectors an encoder emits.

    Parameters
    ----------
    model : Any
        The loaded encoder, read for ``config.hidden_size``.

    Returns
    -------
    int
        The embedding size.

    Raises
    ------
    ValueError
        If the encoder publishes no hidden size.
    """
    size = getattr(getattr(model, "config", None), "hidden_size", None)
    if not isinstance(size, int) or size < 1:
        raise ValueError(
            "The loaded encoder publishes no hidden size, so the shape of an "
            "empty batch cannot be known."
        )
    return size


def _max_length(tokenizer: Any, model: Any) -> int:
    """Return the longest token sequence the tokenizer *and* encoder accept.

    Hugging Face sometimes advertises different limits on the config and the
    tokenizer (``roberta-base`` publishes 514 and 512). Using the larger one
    tokenizes a sequence the encoder then rejects, so the effective limit is
    the smallest advertised one; the unbounded sentinel is ignored.

    Parameters
    ----------
    tokenizer : Any
        The tokenizer, read for ``model_max_length``.
    model : Any
        The encoder, read for its ``max_position_embeddings`` config value.

    Returns
    -------
    int
        The token limit both sides honour.
    """
    limits: List[int] = []
    for candidate in (
        getattr(getattr(model, "config", None), MAX_LENGTH_ATTRIBUTE, None),
        getattr(tokenizer, "model_max_length", None),
    ):
        if isinstance(candidate, int) and 0 < candidate < UNBOUNDED_TOKEN_LIMIT:
            limits.append(candidate)
    return min(limits) if limits else DEFAULT_MAX_LENGTH


class TransformerTextEmbedding(TextEmbeddingConverter):
    """An encoder whose token vectors are pooled into one vector per text.

    Subclasses name one Hugging Face checkpoint in ``MODEL_NAME``, loaded as
    an ``AutoModel`` encoder. Since such a checkpoint has no embedding head,
    ``last_hidden_state`` is pooled with ``pooling_strategy``, ignoring the
    padding of a batch.
    """

    SCHEMA = TransformerEmbeddingSchema
    POOLING_STRATEGIES = POOLING_STRATEGIES

    def __init__(
        self, *, pooling_strategy: str = DEFAULT_POOLING_STRATEGY, **kwargs: Any
    ) -> None:
        """Store the pooling strategy and the shared encoding options.

        Parameters
        ----------
        pooling_strategy : str, optional
            ``"mean"`` or ``"max"``. Default ``"mean"``.
        **kwargs
            Options of :class:`TextEmbeddingConverter`.

        Raises
        ------
        ValueError
            If ``pooling_strategy`` is not supported.
        """
        if pooling_strategy not in self.POOLING_STRATEGIES:
            raise ValueError(
                f"Unknown pooling strategy '{pooling_strategy}', expected one of "
                f"{self.POOLING_STRATEGIES}."
            )
        super().__init__(**kwargs)
        self.pooling_strategy = pooling_strategy
        self.params["pooling_strategy"] = pooling_strategy

    def load_pretrained(self, source: str) -> LoadedTransformer:
        """Load the tokenizer and the encoder.

        Parameters
        ----------
        source : str
            A local directory or a Hub repo id.

        Returns
        -------
        LoadedTransformer
            The tokenizer, the encoder on the chosen device, and the token
            limit shared by both.
        """
        from transformers import AutoModel, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(source)
        model = AutoModel.from_pretrained(source).to(self.device)
        model.eval()
        return LoadedTransformer(
            tokenizer=tokenizer,
            model=model,
            max_length=_max_length(tokenizer, model),
        )

    def encode(self, texts: List[str], role: str = PASSAGE) -> np.ndarray:
        """Encode texts into dense vectors.

        Parameters
        ----------
        texts : list of str
            Texts to encode; None becomes an empty string.
        role : str, optional
            ``"passage"`` or ``"query"``. These encoders take no prompt, so
            the role only has to be a known one.

        Returns
        -------
        np.ndarray
            ``(len(texts), dim)`` float32 array.

        Raises
        ------
        ValueError
            If ``role`` is not a known role.
        """
        if role not in ROLES:
            raise ValueError(f"Unknown role '{role}', expected one of {ROLES}.")
        values = text_values(texts)
        loaded = self.pretrained()
        if not values:
            return np.zeros((0, _hidden_size(loaded.model)), dtype=np.float32)
        if self.overflow_strategy == AGGREGATE:
            return self._embed_windows(loaded, values)
        return self._embed(loaded, values, self.normalize)

    def _embed(
        self, loaded: LoadedTransformer, texts: List[str], normalize: bool
    ) -> np.ndarray:
        """Run the encoder on texts in batches and pool each batch.

        Parameters
        ----------
        loaded : LoadedTransformer
            The loaded tokenizer and encoder.
        texts : list of str
            Texts to encode.
        normalize : bool
            Whether to scale every vector to unit length.

        Returns
        -------
        np.ndarray
            ``(len(texts), dim)`` float32 array.
        """
        import torch

        vectors: List[np.ndarray] = []
        for chunk in batches(texts, self.batch_size):
            encoded = loaded.tokenizer(
                chunk,
                padding=True,
                truncation=True,
                max_length=loaded.max_length,
                return_tensors="pt",
            )
            inputs = {name: value.to(self.device) for name, value in encoded.items()}
            with torch.no_grad():
                outputs = loaded.model(**inputs)
            vectors.append(
                pool_token_embeddings(
                    outputs.last_hidden_state.detach().cpu().numpy(),
                    inputs["attention_mask"].detach().cpu().numpy(),
                    self.pooling_strategy,
                )
            )
        pooled = np.concatenate(vectors, axis=0)
        if normalize:
            return l2_normalize(pooled)
        return pooled.astype(np.float32)

    def _embed_windows(self, loaded: LoadedTransformer, texts: List[str]) -> np.ndarray:
        """Encode each text in token windows and average its windows.

        Parameters
        ----------
        loaded : LoadedTransformer
            The loaded tokenizer and encoder.
        texts : list of str
            Texts to encode.

        Returns
        -------
        np.ndarray
            ``(len(texts), dim)`` float32 array.
        """
        source = _WindowSource(loaded.tokenizer, loaded.max_length)
        windows: List[str] = []
        owners: List[int] = []
        for index, text in enumerate(texts):
            pieces = token_windows(source, text, None)
            windows.extend(pieces)
            owners.extend([index] * len(pieces))
        vectors = self._embed(loaded, windows, False)
        pooled = pool_owner_vectors(vectors, owners, len(texts))
        if self.normalize:
            return l2_normalize(pooled)
        return pooled.astype(np.float32)


class DistilBERTEmbedding(TransformerTextEmbedding):
    """DistilBERT encoder with mean or max pooling."""

    MODEL_NAME = "distilbert/distilbert-base-uncased"
    DOWNLOAD_SIZE_BYTES = 268_000_000
    DISPLAY_NAME = same_label("DistilBERT base uncased")
    DESCRIPTION = MultilingualString(
        en="Compact English encoder pooled into embeddings. Fast on a CPU.",
        es="Codificador inglés compacto agrupado en embeddings. Rápido en CPU.",
        pt="Codificador inglês compacto agrupado em embeddings. Rápido na CPU.",
        de="Kompakter englischer Encoder, zu Embeddings gepoolt. Schnell auf der CPU.",
        zh="紧凑的英文编码器，池化为嵌入。在 CPU 上速度快。",
    )


class RoBERTaEmbedding(TransformerTextEmbedding):
    """RoBERTa encoder with mean or max pooling."""

    MODEL_NAME = "FacebookAI/roberta-base"
    DOWNLOAD_SIZE_BYTES = 499_000_000
    DISPLAY_NAME = same_label("RoBERTa base")
    DESCRIPTION = MultilingualString(
        en="English encoder larger than DistilBERT, pooled into embeddings.",
        es="Codificador inglés más grande que DistilBERT, agrupado en embeddings.",
        pt="Codificador inglês maior que o DistilBERT, agrupado em embeddings.",
        de="Englischer Encoder, größer als DistilBERT, zu Embeddings gepoolt.",
        zh="比 DistilBERT 更大的英文编码器，池化为嵌入。",
    )
