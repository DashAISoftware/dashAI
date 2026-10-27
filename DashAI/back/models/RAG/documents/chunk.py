from typing import Optional, Tuple

from DashAI.back.models.RAG.utils import hash_function


class Chunk:
    """A chunk of text extracted from a document.

    Note:
        ``id`` starts as ``None`` when the chunk is first created in memory
        (see :meth:`BaseChunkingModel.chunk_document`). It is later set to the
        real database primary key by :meth:`ChunkingService._update_chunk_ids`
        after the chunk is persisted.

    Note:
        ``source_positions`` is ``None`` for every stored chunk. It is only set
        on the synthetic chunk a retriever builds when retrieve-then-expand
        widens a retrieved chunk with its neighbours, and it records the
        document positions that were concatenated into it. For such an expanded
        chunk, ``id``, ``page`` and ``document_position`` still identify its
        first covered chunk, while ``text`` and ``source_positions`` cover the
        whole window.
    """

    def __init__(
        self,
        id: Optional[int],
        document_id: int,
        document_position: int,
        text: str,
        page: Optional[int] = None,
        source_positions: Optional[Tuple[int, ...]] = None,
    ):
        """Initialize a Chunk instance.

        Parameters
        ----------
        id : int or None
            The database primary key, or None if not yet persisted.
        document_id : int
            The ``data_document`` id of the parent document.
        document_position : int
            The 0 based position of this chunk within the document.
        text : str
            The text content of the chunk.
        page : int, optional
            Page of the document item the chunk starts in.
        source_positions : tuple of int, optional
            Document positions concatenated into this chunk when a retriever
            expanded it. ``None`` for every stored chunk, which is how an
            already-expanded chunk is recognised and never widened again. On an
            expanded chunk, ``id``, ``page`` and ``document_position`` identify
            the first covered chunk, while ``text`` and ``source_positions``
            cover the whole window.
        """
        self.id: Optional[int] = id
        self.document_id = document_id
        self.document_position = document_position
        self.text = text
        self.page = page
        self.source_positions: Optional[Tuple[int, ...]] = source_positions
        self.hash = hash_function(text)
