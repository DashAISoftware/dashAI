"""E5-Mistral embeddings from a quantized GGUF checkpoint via llama.cpp.

The original E5-Mistral-7B-Instruct repository ships fp16 weights that fill a
GPU on their own. This converter loads the ``Q5_K_M`` GGUF build instead, so the
model runs on the same llama.cpp backend as the local chat models.
"""

import pathlib
from typing import Any, List, Optional

import numpy as np

from DashAI.back.converters.hugging_face.pretrained_tool import batches
from DashAI.back.converters.hugging_face.text_embedding.base import (
    AGGREGATE,
    TextEmbeddingConverter,
    TextEmbeddingSchema,
    l2_normalize,
    pool_owner_vectors,
    same_label,
    text_values,
)
from DashAI.back.converters.hugging_face.text_embedding_roles import (
    PASSAGE,
    QUERY,
    ROLES,
)
from DashAI.back.core.schema_fields import enum_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.utils import (
    LLAMA_DEVICE_ENUM,
    LLAMA_DEVICE_PLACEHOLDER,
    LLAMA_DEVICE_TO_IDX,
)

#: Instruction prepended to every search query, as the model was trained.
E5_MISTRAL_QUERY_PROMPT = (
    "Instruct: Given a web search query, retrieve relevant passages that "
    "answer the query\nQuery: "
)
#: E5-Mistral pools the last token, which must be the EOS token.
EOS_TOKEN = "</s>"
#: Width of the vectors the checkpoint emits.
EMBEDDING_DIM = 4096


class E5MistralGGUFSchema(TextEmbeddingSchema):
    """Encoding options plus the llama.cpp device labels."""

    device: schema_field(
        enum_field(enum=LLAMA_DEVICE_ENUM),
        placeholder=LLAMA_DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en="Device llama.cpp runs on. A GPU offloads every layer.",
            es="Dispositivo en el que corre llama.cpp. Una GPU descarga todas "
            "las capas.",
            pt="Dispositivo em que o llama.cpp roda. Uma GPU descarrega todas "
            "as camadas.",
            de="Gerät, auf dem llama.cpp läuft. Eine GPU lädt alle Schichten aus.",
            zh="llama.cpp 运行的设备。GPU 会卸载所有层。",
        ),
    )  # type: ignore


class E5MistralGGUFEmbedding(TextEmbeddingConverter):
    """E5-Mistral-7B-Instruct embeddings from its Q5_K_M GGUF build.

    Only the quantized file is downloaded. A query is prefixed with the
    instruction the model was trained with, while a passage is encoded as it
    is, which is how the original model is meant to be used.
    """

    SCHEMA = E5MistralGGUFSchema
    MODEL_NAME = "second-state/E5-Mistral-7B-Instruct-Embedding-GGUF"
    GGUF_PATTERN = "*Q5_K_M.gguf"
    DOWNLOAD_SIZE_BYTES = 5_131_409_632
    QUERY_PROMPT = E5_MISTRAL_QUERY_PROMPT
    PASSAGE_PROMPT: Optional[str] = None
    REQUIRES_DOWNLOAD = True
    #: Longest sequence the checkpoint encodes, in tokens.
    MAX_CONTEXT = 4096
    #: Tokens llama.cpp computes per micro-batch. ``n_batch`` stays at
    #: ``MAX_CONTEXT`` so a long sequence is never truncated, but the compute
    #: buffers scale with this value: at ``MAX_CONTEXT`` a 300-token chunk cost
    #: 2.04 s on the reference GPU instead of 0.28 s. It only splits the work,
    #: so the pooled vector is unchanged.
    EMBED_UBATCH = 512
    DISPLAY_NAME = same_label("E5-Mistral-7B-Instruct (Q5_K_M)")
    DESCRIPTION = MultilingualString(
        en="Multilingual retrieval model, quantized to Q5_K_M so it fits on one "
        "GPU. Strong quality, slow on a CPU.",
        es="Modelo multilingüe de recuperación, cuantizado a Q5_K_M para caber "
        "en una GPU. Gran calidad, lento en CPU.",
        pt="Modelo multilíngue de recuperação, quantizado em Q5_K_M para caber "
        "em uma GPU. Ótima qualidade, lento na CPU.",
        de="Mehrsprachiges Retrieval-Modell, auf Q5_K_M quantisiert, damit es "
        "auf eine GPU passt. Starke Qualität, langsam auf der CPU.",
        zh="多语言检索模型，量化为 Q5_K_M 以便单卡运行。质量出色，CPU 上较慢。",
    )

    def __init__(self, device: str = LLAMA_DEVICE_PLACEHOLDER, **kwargs: Any) -> None:
        """Store the schema device label and the shared encoding options.

        llama.cpp does not use the torch device string, so the label the user
        picked is kept aside for :meth:`load_pretrained`.

        Parameters
        ----------
        device : str, optional
            Device label from :func:`device_field`.
        **kwargs
            Options of :class:`TextEmbeddingConverter`.
        """
        self._device_label = device
        super().__init__(device=device, **kwargs)

    @classmethod
    def hf_repos(cls) -> List[Any]:
        """Return the one repo entry, restricted to the quantized file.

        Returns
        -------
        list of tuple
            ``[(MODEL_NAME, "model", [GGUF_PATTERN])]``, so the snapshot
            download fetches the Q5_K_M checkpoint and nothing else.
        """
        return [(cls.MODEL_NAME, "model", [cls.GGUF_PATTERN])]

    @classmethod
    def is_downloaded(cls) -> bool:
        """Return whether the Q5_K_M checkpoint is on disk.

        A non-empty repo folder is not enough: a folder holding only a README
        or a half-written download must not pass as finished.

        Returns
        -------
        bool
            ``True`` when a file matching :data:`GGUF_PATTERN` exists.
        """
        repo_dir = cls._repo_dir(cls.MODEL_NAME)
        minimum_size = int(cls.DOWNLOAD_SIZE_BYTES * 0.95)
        return any(
            path.is_file() and path.stat().st_size >= minimum_size
            for path in repo_dir.glob(cls.GGUF_PATTERN)
        )

    @classmethod
    def _local_gguf_path(cls) -> pathlib.Path:
        """Return the downloaded Q5_K_M checkpoint.

        Returns
        -------
        pathlib.Path
            The checkpoint file.

        Raises
        ------
        RuntimeError
            If no file matching :data:`GGUF_PATTERN` exists, naming the repo
            directory and the pattern the user has to re-download.
        """
        repo_dir = cls._repo_dir(cls.MODEL_NAME)
        matches = sorted(
            path for path in repo_dir.glob(cls.GGUF_PATTERN) if path.is_file()
        )
        if not matches:
            raise RuntimeError(
                f"{cls.__name__} could not find a downloaded GGUF file for repo "
                f"{cls.MODEL_NAME!r} in '{repo_dir}' matching GGUF_PATTERN "
                f"{cls.GGUF_PATTERN!r}. The download is missing or incomplete; "
                "re-download the component before using it."
            )
        return matches[0]

    def _gpu_index(self) -> int:
        """Return the llama.cpp GPU index of the chosen device.

        Returns
        -------
        int
            The index, or -1 when the chosen device is the CPU.

        Raises
        ------
        ValueError
            If a non-CPU label is not one llama.cpp detected.
        """
        if self._device_label == "CPU":
            return -1
        index = LLAMA_DEVICE_TO_IDX.get(self._device_label)
        if index is None:
            raise ValueError(
                f"Device {self._device_label!r} is not available to llama.cpp; "
                f"available devices: {list(LLAMA_DEVICE_TO_IDX)}."
            )
        return index

    def _n_gpu_layers(self) -> int:
        """Return how many layers llama.cpp offloads to the GPU.

        Returns
        -------
        int
            ``-1`` (every layer) on a GPU device, ``0`` on the CPU.
        """
        return -1 if self._gpu_index() >= 0 else 0

    def _main_gpu(self) -> int:
        """Return the GPU llama.cpp keeps the model's non-offloaded part in.

        Returns
        -------
        int
            The chosen index, or 0 when running on the CPU.
        """
        return max(self._gpu_index(), 0)

    def load_pretrained(self, source: str) -> Any:
        """Load the quantized checkpoint with llama.cpp in embedding mode.

        Parameters
        ----------
        source : str
            Where the mixin resolved the model from. Unused: the file is read
            from the component's own download folder.

        Returns
        -------
        llama_cpp.Llama
            The loaded model, ready for :meth:`encode`.
        """
        from llama_cpp import LLAMA_POOLING_TYPE_LAST, Llama

        return Llama(
            model_path=str(self._local_gguf_path()),
            embedding=True,
            n_ctx=self.MAX_CONTEXT,
            n_batch=self.MAX_CONTEXT,
            n_ubatch=self.EMBED_UBATCH,
            n_gpu_layers=self._n_gpu_layers(),
            main_gpu=self._main_gpu(),
            pooling_type=LLAMA_POOLING_TYPE_LAST,
            verbose=False,
        )

    def encode(self, texts: List[str], role: str = PASSAGE) -> np.ndarray:
        """Encode texts into dense vectors.

        Parameters
        ----------
        texts : list of str
            Texts to encode; None becomes an empty string.
        role : str, optional
            ``"passage"`` for indexed text, ``"query"`` for a search query,
            which is prefixed with :data:`QUERY_PROMPT`.

        Returns
        -------
        np.ndarray
            ``(len(texts), model.n_embd())`` float32 array.

        Raises
        ------
        ValueError
            If ``role`` is not a known role.
        """
        if role not in ROLES:
            raise ValueError(f"Unknown role '{role}', expected one of {ROLES}.")
        values = text_values(texts)
        if not values:
            return np.zeros((0, EMBEDDING_DIM), dtype=np.float32)
        model = self.pretrained()
        if self.overflow_strategy == AGGREGATE:
            return self._encode_aggregated(model, values, role)
        return self._encode_texts(model, values, role)

    def _input_text(self, text: str, role: str) -> str:
        """Return the text with the role instruction the model expects."""
        if role == QUERY and self.QUERY_PROMPT:
            return f"{self.QUERY_PROMPT}{text}"
        return text

    def _encode_texts(self, model: Any, texts: List[str], role: str) -> np.ndarray:
        """Embed texts in batches, appending the EOS token last-token pooling needs."""
        prepared = [
            self._truncate_with_eos(model, self._input_text(text, role))
            for text in texts
        ]
        rows: List[np.ndarray] = []
        for chunk in batches(prepared, self.batch_size):
            vectors = np.asarray(
                model.embed(chunk, normalize=False, truncate=True),
                dtype=np.float32,
            )
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            rows.append(vectors)
        pooled = np.concatenate(rows, axis=0)
        if self.normalize:
            return l2_normalize(pooled)
        return pooled.astype(np.float32)

    def _truncate_with_eos(self, model: Any, text: str) -> str:
        """Cut a text to the context budget while keeping the final EOS token."""
        budget = self.MAX_CONTEXT - 1
        tokens = model.tokenize(text.encode("utf-8"))
        if len(tokens) > budget:
            text = bytes(model.detokenize(tokens[:budget])).decode(
                "utf-8", errors="ignore"
            )
        return f"{text}{EOS_TOKEN}"

    def _encode_aggregated(self, model: Any, texts: List[str], role: str) -> np.ndarray:
        """Split long texts into token windows, embed each and average."""
        windows: List[str] = []
        owners: List[int] = []
        for index, text in enumerate(texts):
            pieces = self._token_windows(model, self._input_text(text, role))
            windows.extend(pieces)
            owners.extend([index] * len(pieces))
        vectors = self._encode_windows(model, windows)
        pooled = pool_owner_vectors(vectors, owners, len(texts))
        if self.normalize:
            return l2_normalize(pooled)
        return pooled.astype(np.float32)

    def _token_windows(self, model: Any, text: str) -> List[str]:
        """Split a text into windows that fit the context, EOS included."""
        budget = self.MAX_CONTEXT - 1
        tokens = model.tokenize(text.encode("utf-8"))
        if len(tokens) <= budget:
            return [f"{text}{EOS_TOKEN}"]
        pieces: List[str] = []
        for start in range(0, len(tokens), budget):
            window = model.detokenize(tokens[start : start + budget])
            decoded = bytes(window).decode("utf-8", errors="ignore")
            pieces.append(f"{decoded}{EOS_TOKEN}")
        return pieces

    def _encode_windows(self, model: Any, windows: List[str]) -> np.ndarray:
        """Embed token windows in batches."""
        rows: List[np.ndarray] = []
        for chunk in batches(windows, self.batch_size):
            vectors = np.asarray(
                model.embed(chunk, normalize=False, truncate=True),
                dtype=np.float32,
            )
            if vectors.ndim == 1:
                vectors = vectors.reshape(1, -1)
            rows.append(vectors)
        return np.concatenate(rows, axis=0)
