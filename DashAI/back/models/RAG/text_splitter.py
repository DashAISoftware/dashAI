from typing import List, Dict, Tuple
class TextSplitter:
    """
    A simple text splitter that splits text into chunks of a specified size with overlap.
    This is useful for processing large texts in smaller parts.
    """
    def __init__(self, chunk_size=1000, chunk_overlap=200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split_text(self, text: str) -> List[str]:
        """
        Split the text into chunks of specified size with overlap.
        Args:
            text (str): The text to be split.
        Returns:
            List[str]: A list of text chunks.
        """
        chunks = []
        for i in range(0, len(text), self.chunk_size - self.chunk_overlap):
            chunk = text[i:i + self.chunk_size]
            if chunk:
                chunks.append(chunk)
        return chunks

    def split_documents_texts(self, documents: Dict[str, str]) -> List[Tuple[str, int, str]]:
        """
        Split the documents into chunks of text.
        Args:
            documents (Dict[str, str]): A dictionary of documents with filenames as keys and content as values.
        Returns:
            List[Tuple[str, int, str]]: A list of tuples containing the filename, chunk index, and chunk content.
        """
        chunked_documents = []
        for filename, content in documents.items():
            chunks = self.split_text(content)
            for i, chunk in enumerate(chunks):
                chunked_documents.append(
                    (filename, i, chunk)
                )
        return chunked_documents