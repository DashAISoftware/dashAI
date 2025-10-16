from typing import Any, List
import numpy as np

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk


class ChunkEmbedding:
    def __init__(
            self, 
            document: BaseDocument,
            chunk: Chunk,
            embedding: List[float]|np.ndarray|Any,
    ):
        self.document = document
        self.chunk = chunk
        self.embedding = embedding