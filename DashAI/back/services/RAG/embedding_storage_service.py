"""Service for managing embedding matrix persistence on disk and in DB."""

import logging
import os
import shutil

from DashAI.back.services.RAG.retriever_db_service import RetrieverDBService

logger = logging.getLogger(__name__)

EMBEDDINGS_DIRNAME = "embeddings"
EMBEDDINGS_FILENAME = "embeddings.npy"


class EmbeddingStorageService:
    """Manages embedding matrix persistence: numpy .npy files on disk + DB records.

    Embedding matrices are stored as .npy files in directories like:
    ``{env_RAG_path}/embeddings/doc_id-{doc_id}__content-{content_key}__
    embedding_model_id-{embedding_model_id}/embeddings.npy``

    The path is addressed by the document's *content*, not by the chunk set: two
    sessions that chunk the same document the same way share one matrix, while
    each keeps its own ``RAGEmbeddingMatrix`` row pointing at it.
    """

    def __init__(self, env_RAG_path: str, db_service: RetrieverDBService):  # noqa: N803
        """Initialise with the base RAG directory path and DB service.

        Parameters
        ----------
        env_RAG_path : str
            Base RAG directory path from config.
        db_service : RetrieverDBService
            Service for database operations on retriever models.
        """
        self._env_RAG_path = env_RAG_path
        self._db_service = db_service

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_matrix_dir_name(
        doc_id: int, content_key: str, embedding_model_id: int
    ) -> str:
        """Build the content-addressed folder name of one document's matrix.

        Parameters
        ----------
        doc_id : int
            Owning document id.
        content_key : str
            Content hash of the document's chunks, independent of any database
            id, so the same content resolves to the same folder across sessions.
        embedding_model_id : int
            Embedding model identifier.

        Returns
        -------
        str
            ``doc_id-{doc_id}__content-{content_key}__embedding_model_id-{id}``.
        """
        return (
            f"doc_id-{doc_id}__content-{content_key}__"
            f"embedding_model_id-{embedding_model_id}"
        )

    def _matrix_dir(
        self, doc_id: int, content_key: str, embedding_model_id: int
    ) -> str:
        """Build the directory path for a specific embedding matrix.

        Format: ``{env_RAG_path}/embeddings/doc_id-{doc_id}__
        content-{content_key}__embedding_model_id-{embedding_model_id}``
        """
        return os.path.join(
            self._env_RAG_path,
            EMBEDDINGS_DIRNAME,
            self.build_matrix_dir_name(doc_id, content_key, embedding_model_id),
        )

    def _matrix_path(
        self, doc_id: int, content_key: str, embedding_model_id: int
    ) -> str:
        """Full path to the ``embeddings.npy`` file.

        Delegates to :meth:`_matrix_dir` and appends the filename.
        """
        return os.path.join(
            self._matrix_dir(doc_id, content_key, embedding_model_id),
            EMBEDDINGS_FILENAME,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def exists(self, doc_id: int, content_key: str, embedding_model_id: int) -> bool:
        """Check whether an ``embeddings.npy`` file exists on disk.

        Parameters
        ----------
        doc_id : int
            Owning document id.
        content_key : str
            Content hash of the document's chunks.
        embedding_model_id : int
            Embedding model identifier.

        Returns
        -------
        bool
            ``True`` if the file exists, ``False`` otherwise.
        """
        return os.path.isfile(
            self._matrix_path(doc_id, content_key, embedding_model_id)
        )

    @staticmethod
    def delete_storage(storage_folder: str) -> None:
        """Recursively delete a storage directory if it exists.

        Uses :func:`shutil.rmtree` and silently ignores missing folders.

        Parameters
        ----------
        storage_folder : str
            Absolute path to the directory to remove.
        """
        if os.path.isdir(storage_folder):
            try:
                shutil.rmtree(storage_folder)
            except OSError as exc:
                logger.warning(
                    "Failed to remove storage folder %s: %s",
                    storage_folder,
                    exc,
                )
