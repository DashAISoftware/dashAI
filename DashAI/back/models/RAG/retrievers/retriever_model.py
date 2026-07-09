import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Final, List, Tuple

from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.base_model import BaseModel
from DashAI.back.models.RAG.documents import Chunk
from DashAI.back.models.RAG.exceptions import RAGWorkflowError


class RetrieverModel(BaseModel, ABC):
    """
    Component: abstract base class for all retriever models.

    Implements the Component role in the Composite design pattern (GoF).
    """

    TYPE: Final[str] = "RetrieverModel"
    FLAGS: list[str] = ["abstract"]
    DISPLAY_NAME: str = MultilingualString(
        en="Retriever",
        es="Recuperador",
    )
    DESCRIPTION: str = MultilingualString(
        en="Document retrieval component.",
        es="Componente de recuperación de documentos.",
    )
    COLOR: str = "#9C27B0"
    ICON: str = "Search"

    env_rag_path: str | os.PathLike | None
    chunks: Dict[int, Dict[int, Chunk]]
    chunking_model_id: int | None
    params: Dict[str, Any]

    def __init__(self, **kwargs):
        self._db_id: int | None = None
        self.params = kwargs

    # ── Canonical ID (RAGRetriever.id for all retrievers) ──────────

    def get_id(self) -> int | None:
        return self._db_id

    def set_id(self, id: int) -> None:
        if self._db_id is not None:
            raise RAGWorkflowError(
                f"ID is already set to {self._db_id}, cannot reassign to {id}."
            )
        self._db_id = id

    # ── Validation ──────────────────────────────────────────────────

    def _validate_chunks_dict(self) -> None:
        if not isinstance(self.chunks, dict):
            raise ValueError("Chunks must be a dictionary.")
        for doc_id, doc_chunks in self.chunks.items():
            if not isinstance(doc_id, int):
                raise ValueError(f"Document ID {doc_id} must be an integer.")
            if not isinstance(doc_chunks, dict):
                raise ValueError(
                    f"Chunks for document ID {doc_id} must be a dictionary."
                )
            for chunk_id, chunk in doc_chunks.items():
                if not isinstance(chunk_id, int):
                    raise ValueError(
                        f"Chunk ID {chunk_id} in document ID {doc_id} must be an integer."
                    )
                if not isinstance(chunk, Chunk):
                    raise ValueError(
                        f"Chunk {chunk_id} in document ID {doc_id} must be an instance of Chunk."
                    )
                if chunk.document_id != doc_id:
                    raise ValueError(
                        f"Chunk {chunk_id} document_id {chunk.document_id} != doc ID {doc_id}."
                    )

    # ── Infrastructure injection ───────────────────────────────────

    def inject_infra(
        self,
        env_rag_path: str | os.PathLike,
        chunks: Dict[int, Dict[int, Chunk]],
        persistence: Any,
    ) -> None:
        """Inject runtime infrastructure *after* schema validation.

        Subclasses **must** store the three arguments as instance
        attributes.  Raises ``TypeError`` if any argument has an
        unexpected type.
        """
        self.env_rag_path = env_rag_path
        self.chunks = chunks
        self._persistence = persistence
        self._validate_chunks_dict()

    # ── Post-infra initialisation ────────────────────────────────────

    def init_model(self) -> None:
        """Called by the factory **after** ``inject_infra()``.

        Subclasses restore saved state (``load()``) or compute initial
        state (``_fit()``, ``_init_embedding()``).  Default is a no-op.
        """

    # ── Retrieval interface ─────────────────────────────────────────

    @abstractmethod
    def retrieve(self, query, **kwargs) -> List[Chunk]:
        raise NotImplementedError

    @abstractmethod
    def score_chunks(self, chunk_ids: List[int], query: str) -> List[Tuple[int, float]]:
        raise NotImplementedError

    @property
    def retrieval_top_k(self) -> int:
        raise NotImplementedError

    # ── Child management (Composite pattern) ────────────────────────

    def add(self, child: "RetrieverModel") -> None:
        raise NotImplementedError

    def remove(self, child: "RetrieverModel") -> None:
        raise NotImplementedError

    def get_children(self) -> List["RetrieverModel"]:
        raise NotImplementedError

    # ── BaseModel contract ──────────────────────────────────────────

    def save(self, filename: str = "") -> None:
        pass

    def load(self, filename: str = "") -> None:
        pass

    def train(self, **kwargs):
        return
