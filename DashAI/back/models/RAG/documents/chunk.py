from DashAI.back.models.RAG.utils import hash_function


class Chunk:
    """A class representing a chunk of a document."""

    def __init__(
        self,
        id: int,
        document_id: str,
        document_position: int,
        text: str,
    ):
        self.id = id
        self.document_id = document_id
        self.document_position = document_position
        self.text = text
        self.hash = hash_function(text)
