"""Document dataloader for office, web and email files using unstructured."""

import hashlib
import importlib
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

from DashAI.back.core.schema_fields import BaseSchema, bool_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.document_dataloader import (
    DocumentDataLoader,
    DocumentLoaderError,
)
from DashAI.back.dataloaders.classes.document_elements import table_text
from DashAI.back.dependencies.downloads.downloadable import (
    DownloadableMixin,
    ProgressReporter,
)

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_document import (
        DashAIDocument,
        DocumentItem,
    )

SPACY_MODEL = "en_core_web_sm"
SPACY_MODEL_VERSION = "3.8.0"
SPACY_MODEL_URL = (
    "https://github.com/explosion/spacy-models/releases/download/"
    f"{SPACY_MODEL}-{SPACY_MODEL_VERSION}/"
    f"{SPACY_MODEL}-{SPACY_MODEL_VERSION}-py3-none-any.whl"
)
SPACY_MODEL_SHA256 = "1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85"
DOWNLOAD_CHUNK_BYTES = 1 << 16
PRIVACY_ENVIRONMENT = {
    "SCARF_NO_ANALYTICS": "true",
    "UNSTRUCTURED_DISABLE_NOTICE": "1",
}
CATEGORY_KINDS: Dict[str, str] = {
    "Header": "page_header",
    "Footer": "page_footer",
    "FigureCaption": "caption",
    "CodeSnippet": "code",
}
SKIPPED_CATEGORIES = frozenset({"PageBreak", "Image"})
HEADER_FOOTER_KINDS = frozenset({"page_header", "page_footer"})


class UnstructuredDocumentSchema(BaseSchema):
    """Parameters for UnstructuredDocumentDataLoader."""

    include_headers_footers: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en="Keep the page headers and footers unstructured detects.",
            es=("Conserva los encabezados y pies de página que detecta unstructured."),
            pt="Mantém os cabeçalhos e rodapés que o unstructured detecta.",
            de="Behält die Kopf- und Fußzeilen, die unstructured erkennt.",
            zh="保留 unstructured 识别出的页眉和页脚。",
        ),
        alias=MultilingualString(
            en="Include headers and footers",
            es="Incluir encabezados y pies de página",
            pt="Incluir cabeçalhos e rodapés",
            de="Kopf- und Fußzeilen einbeziehen",
            zh="包含页眉和页脚",
        ),
    )  # type: ignore


class UnstructuredDocumentDataLoader(DownloadableMixin, DocumentDataLoader):
    """Parse office, web and email files with unstructured's partitioners.

    Each element unstructured returns becomes one item named after its
    category: Title becomes a heading, ListItem a list item, Table a table
    with its rows, Header and Footer page headers and footers, FigureCaption
    a caption and CodeSnippet code; every other text element is a paragraph.
    Heading levels and list depths count from the shallowest one in the
    file. unstructured's usage analytics and notice are turned off.

    unstructured classifies text with the spaCy model ``en_core_web_sm``,
    which it would otherwise download and install into the environment on
    first use. Here it is a component download instead: the pinned wheel is
    unpacked into ``component_dir()``, which is put on ``sys.path`` while
    parsing, and the loader refuses to parse until it is present.
    """

    SCHEMA: ClassVar[BaseSchema] = UnstructuredDocumentSchema
    DOWNLOAD_SIZE_BYTES = 12806118
    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
        {".docx", ".pptx", ".xlsx", ".html", ".htm", ".md", ".eml", ".msg"}
    )
    DISPLAY_NAME = MultilingualString(
        en="unstructured",
        es="unstructured",
        pt="unstructured",
        de="unstructured",
        zh="unstructured",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Reads Word, PowerPoint and Excel files, web pages, Markdown and "
            "emails (docx, pptx, xlsx, html, md, eml, msg) with unstructured. "
            "Stores each element it detects as one text item named as a "
            "heading, list item, table, caption, code or paragraph, with the "
            "slide or sheet number as its page."
            " [https://github.com/Unstructured-IO/unstructured]"
            "(https://github.com/Unstructured-IO/unstructured)"
        ),
        es=(
            "Lee archivos de Word, PowerPoint y Excel, páginas web, Markdown y "
            "correos (docx, pptx, xlsx, html, md, eml, msg) con unstructured. "
            "Guarda cada elemento que detecta como un elemento de texto "
            "nombrado como encabezado, elemento de lista, tabla, leyenda, "
            "código o párrafo, con el número de diapositiva u hoja como su "
            "página."
            " [https://github.com/Unstructured-IO/unstructured]"
            "(https://github.com/Unstructured-IO/unstructured)"
        ),
        pt=(
            "Lê arquivos do Word, PowerPoint e Excel, páginas web, Markdown e "
            "e-mails (docx, pptx, xlsx, html, md, eml, msg) com unstructured. "
            "Guarda cada elemento que detecta como um item de texto nomeado "
            "como cabeçalho, item de lista, tabela, legenda, código ou "
            "parágrafo, com o número do slide ou da planilha como sua página."
            " [https://github.com/Unstructured-IO/unstructured]"
            "(https://github.com/Unstructured-IO/unstructured)"
        ),
        de=(
            "Liest Word-, PowerPoint- und Excel-Dateien, Webseiten, Markdown "
            "und E-Mails (docx, pptx, xlsx, html, md, eml, msg) mit "
            "unstructured. Speichert jedes erkannte Element als Textelement, "
            "benannt als Überschrift, Listenelement, Tabelle, Beschriftung, "
            "Code oder Absatz, mit der Folien- oder Blattnummer als Seite."
            " [https://github.com/Unstructured-IO/unstructured]"
            "(https://github.com/Unstructured-IO/unstructured)"
        ),
        zh=(
            "使用 unstructured 读取 Word、PowerPoint 和 Excel 文件、网页、"
            "Markdown 和电子邮件（docx、pptx、xlsx、html、md、eml、msg）。"
            "将识别出的每个元素保存为一个文本项，命名为章节标题、列表项、表格、"
            "题注、代码或段落，并以幻灯片或工作表编号作为页码。"
            "[https://github.com/Unstructured-IO/unstructured]"
            "(https://github.com/Unstructured-IO/unstructured)"
        ),
    )

    @classmethod
    def is_downloaded(cls) -> bool:
        """Return whether the spaCy model is unpacked in ``component_dir()``.

        Returns
        -------
        bool
            True when both the model package and its ``dist-info`` folder,
            which ``spacy.load`` needs to find it by name, are present.
        """
        target = cls.component_dir()
        return (target / SPACY_MODEL / "__init__.py").is_file() and any(
            target.glob(f"{SPACY_MODEL}-*.dist-info")
        )

    @classmethod
    def download(cls, report: Optional[ProgressReporter] = None) -> None:
        """Download the pinned spaCy model wheel and unpack it.

        Parameters
        ----------
        report : ProgressReporter, optional
            Called with the fraction downloaded each time it grows by a
            percent.

        Raises
        ------
        ValueError
            If the downloaded wheel does not match ``SPACY_MODEL_SHA256``.
        httpx.HTTPError
            If the wheel cannot be downloaded.
        """
        import zipfile

        import httpx

        target = cls.component_dir()
        target.mkdir(parents=True, exist_ok=True)
        wheel = target / SPACY_MODEL_URL.rsplit("/", 1)[-1]
        digest = hashlib.sha256()
        message = f"Downloading spaCy model {SPACY_MODEL} {SPACY_MODEL_VERSION}"
        with httpx.stream(
            "GET", SPACY_MODEL_URL, follow_redirects=True, timeout=60
        ) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length") or 0)
            received = 0
            reported = -1
            with open(wheel, "wb") as handle:
                for chunk in response.iter_bytes(DOWNLOAD_CHUNK_BYTES):
                    handle.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    percent = received * 100 // total if total else None
                    if report is not None and percent != reported:
                        report(None if percent is None else percent / 100, message)
                        reported = percent
        if digest.hexdigest() != SPACY_MODEL_SHA256:
            wheel.unlink(missing_ok=True)
            raise ValueError(
                f"The downloaded {SPACY_MODEL} wheel does not match its pinned SHA-256."
            )
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(target)
        wheel.unlink()

    @staticmethod
    def table_rows(html: str) -> Tuple[List[List[str]], bool]:
        """Read the rows of a table from the HTML unstructured gives it.

        Parameters
        ----------
        html : str
            The ``text_as_html`` metadata of a Table element.

        Returns
        -------
        Tuple[List[List[str]], bool]
            Each row as its cells' text, and whether the first row is made
            of header cells only.
        """
        import lxml.html

        rows = []
        header = False
        for index, row in enumerate(lxml.html.fromstring(html).iter("tr")):
            cells = [cell for cell in row if cell.tag in ("td", "th")]
            if index == 0:
                header = bool(cells) and all(cell.tag == "th" for cell in cells)
            rows.append([cell.text_content().strip() for cell in cells])
        return rows, header

    @staticmethod
    def _shallowest(elements: List[Any], category: str) -> int:
        """Return the smallest category depth among elements of one category."""
        depths = [
            element.metadata.category_depth
            for element in elements
            if element.category == category
            and element.metadata.category_depth is not None
        ]
        return min(depths, default=0)

    def _element_item(
        self, element: Any, title_base: int, list_base: int
    ) -> Optional["DocumentItem"]:
        """Turn one unstructured element into a document item.

        Parameters
        ----------
        element : unstructured.documents.elements.Element
            The element.
        title_base : int
            Depth of the shallowest Title in the file, heading level 1.
        list_base : int
            Depth of the shallowest ListItem in the file, list depth 0.

        Returns
        -------
        Optional[DocumentItem]
            The item, None for page breaks, images and blank elements.
        """
        from DashAI.back.dataloaders.classes.dashai_document import DocumentItem
        from DashAI.back.types.value_types import Text

        text = (element.text or "").strip()
        if element.category in SKIPPED_CATEGORIES or not text:
            return None
        depth = element.metadata.category_depth
        page = element.metadata.page_number
        kind, attrs = CATEGORY_KINDS.get(element.category, "paragraph"), {}
        if element.category == "Title":
            level = 1 if depth is None else depth - title_base + 1
            kind, attrs = "heading", {"level": min(max(level, 1), 6)}
        elif element.category == "ListItem":
            kind = "list_item"
            attrs = {"depth": 0 if depth is None else max(depth - list_base, 0)}
        elif element.category == "Table" and element.metadata.text_as_html:
            rows, header = self.table_rows(element.metadata.text_as_html)
            if rows:
                return DocumentItem(
                    type=Text,
                    content=table_text(rows),
                    page=page,
                    kind="table",
                    attrs={"rows": rows, "header": header},
                )
        return DocumentItem(type=Text, content=text, page=page, kind=kind, attrs=attrs)

    @classmethod
    def _partition(cls, file_path: str) -> List[Any]:
        """Run unstructured on a file with its analytics turned off.

        ``component_dir()`` joins ``sys.path`` so ``spacy.load`` finds the
        downloaded model by name. The content type comes from the file
        extension, so unstructured never needs libmagic. On Windows the
        ``magic`` module is blocked before unstructured imports it:
        python-magic there only finds MSYS or Cygwin builds of libmagic on
        PATH (such as Git's ``msys-magic-1.dll``), and loading one into a
        native Python process hangs or crashes it.

        Parameters
        ----------
        file_path : str
            Path of the file.

        Returns
        -------
        List[Any]
            The elements unstructured returns, in reading order.
        """
        for name, value in PRIVACY_ENVIRONMENT.items():
            os.environ.setdefault(name, value)
        if sys.platform == "win32":
            sys.modules.setdefault("magic", None)
        model_path = str(cls.component_dir())
        if model_path not in sys.path:
            sys.path.append(model_path)
            importlib.invalidate_caches()

        from unstructured.file_utils.model import FileType
        from unstructured.partition.auto import partition

        file_type = FileType.from_extension(Path(file_path).suffix.lower())
        return partition(
            filename=file_path,
            content_type=file_type.mime_type if file_type else None,
        )

    def load_document(self, file_path: str, params: Dict[str, Any]) -> "DashAIDocument":
        """Parse a file with unstructured.

        Parameters
        ----------
        file_path : str
            Path of the file.
        params : Dict[str, Any]
            ``include_headers_footers``; missing keys take the default.

        Returns
        -------
        DashAIDocument
            One text item per element in reading order, with the slide or
            sheet number as page where unstructured gives one.

        Raises
        ------
        DocumentLoaderError
            If the spaCy model is not downloaded or unstructured cannot read
            the file.
        """
        from DashAI.back.dataloaders.classes.dashai_document import DashAIDocument

        resolved = self.resolve_params(params)
        if not self.is_downloaded():
            raise DocumentLoaderError(
                f"{type(self).__name__} must be downloaded before use."
            )
        try:
            elements = self._partition(file_path)
        except Exception as e:
            raise DocumentLoaderError(
                f"unstructured failed to read {file_path}: {e}"
            ) from e
        title_base = self._shallowest(elements, "Title")
        list_base = self._shallowest(elements, "ListItem")
        items = [
            item
            for item in (
                self._element_item(element, title_base, list_base)
                for element in elements
            )
            if item is not None
            and (
                resolved["include_headers_footers"]
                or item.kind not in HEADER_FOOTER_KINDS
            )
        ]
        pages = [
            element.metadata.page_number
            for element in elements
            if element.metadata.page_number is not None
        ]
        return DashAIDocument.from_items(
            items,
            metadata=self.build_metadata(
                file_path, resolved, max(pages) if pages else None
            ),
        )
