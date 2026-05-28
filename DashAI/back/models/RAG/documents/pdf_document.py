from typing import Any, Dict, Optional

from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.utils import hash_function


class PDFDocument(BaseDocument):
    """
    Class representing a PDF document.
    """

    def __init__(
        self,
        id: int,
        file_name: str,
        file_path: str,
        created: Optional[str] = None,
        optional_metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ):
        """
        Initialize the document.
        Args (from database):
            id (int): The unique identifier of the document.
            file_name (str): The name of the file.
            file_path (str): The path to the file.
            created (Optional[str]): The creation date of the document.
            optional_metadata (Optional[Dict[str, Any]]): Additional metadata for the document.
        """
        self.PARSER = kwargs.get("parser", "textract")
        file_hash = hash_function(file_path)
        super().__init__(
            id=id,
            file_name=file_name,
            file_path=file_path,
            file_hash=file_hash,
            created=created,
            optional_metadata=optional_metadata,
        )

    def get_text(self) -> str:
        if self.PARSER == "PyPDF2":
            from PyPDF2 import PdfReader

            reader = PdfReader(self.file_path)
            if not reader.pages:
                raise ValueError(
                    f"The PDF file {self.file_path} is empty or not valid."
                )

            # Extract text from all pages
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            return text.strip()
        elif self.PARSER == "textract":
            import re

            import textract

            try:
                text = textract.process(self.file_path, output_encoding="utf-8").decode(
                    "utf-8"
                )

                def limpiar_texto(texto):
                    # Mantiene letras españolas, números, espacios, puntuación y saltos de línea normales
                    # Elimina caracteres de control como \x0c, \r, etc.

                    # Opción 1: Eliminar solo caracteres de control específicos
                    texto = re.sub(
                        r"[\x00-\x1f\x7f]", " ", texto
                    )  # Reemplaza por espacio
                    texto = re.sub(r"\s+", " ", texto)  # Normaliza espacios múltiples

                    # Opción 2: Eliminar pero mantener saltos de línea (recomendado)
                    # texto = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', '', texto)

                    return texto.strip()

                text = limpiar_texto(text)
                return text.strip()
            except Exception as e:
                raise ValueError(
                    f"Error extracting text from PDF file {self.file_path}: {str(e)}"
                )
        else:
            raise ValueError(f"Unsupported parser: {self.PARSER}")

    def get_metadata(self):
        return self.optional_metadata if self.optional_metadata else {}
