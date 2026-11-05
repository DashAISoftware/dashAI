"""Document dataloader for Word files using python-docx."""

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional, Tuple

from DashAI.back.core.schema_fields import BaseSchema, bool_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.document_dataloader import (
    DocumentDataLoader,
    DocumentLoaderError,
)
from DashAI.back.dataloaders.classes.document_elements import table_text

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_document import (
        DashAIDocument,
        DocumentItem,
    )

log = logging.getLogger(__name__)

STYLE_KINDS: Dict[str, str] = {
    "title": "title",
    "quote": "quote",
    "intense quote": "quote",
    "caption": "caption",
    "html preformatted": "code",
}
UNORDERED_FORMATS = frozenset({"bullet", "none", ""})


class PythonDocxDocumentSchema(BaseSchema):
    """Parameters for PythonDocxDocumentDataLoader."""

    extract_images: schema_field(
        bool_field(),
        placeholder=True,
        description=MultilingualString(
            en=(
                "Store the images embedded in the text as image items, right "
                "after the paragraph that holds them."
            ),
            es=(
                "Guarda las imágenes incrustadas en el texto como elementos de "
                "imagen, justo después del párrafo que las contiene."
            ),
            pt=(
                "Guarda as imagens incorporadas no texto como itens de imagem, "
                "logo após o parágrafo que as contém."
            ),
            de=(
                "Speichert die in den Text eingebetteten Bilder als "
                "Bildelemente, direkt nach dem Absatz, der sie enthält."
            ),
            zh="将正文中嵌入的图像保存为图像项，紧随包含它们的段落之后。",
        ),
        alias=MultilingualString(
            en="Extract images",
            es="Extraer imágenes",
            pt="Extrair imagens",
            de="Bilder extrahieren",
            zh="提取图像",
        ),
    )  # type: ignore
    include_headers_footers: schema_field(
        bool_field(),
        placeholder=False,
        description=MultilingualString(
            en=(
                "Store the text of the page headers before the body and the "
                "text of the page footers after it."
            ),
            es=(
                "Guarda el texto de los encabezados de página antes del cuerpo "
                "y el de los pies de página después de él."
            ),
            pt=(
                "Guarda o texto dos cabeçalhos de página antes do corpo e o "
                "dos rodapés depois dele."
            ),
            de=(
                "Speichert den Text der Kopfzeilen vor dem Haupttext und den "
                "der Fußzeilen danach."
            ),
            zh="将页眉文本保存在正文之前，页脚文本保存在正文之后。",
        ),
        alias=MultilingualString(
            en="Include headers and footers",
            es="Incluir encabezados y pies de página",
            pt="Incluir cabeçalhos e rodapés",
            de="Kopf- und Fußzeilen einbeziehen",
            zh="包含页眉和页脚",
        ),
    )  # type: ignore


class PythonDocxDocumentDataLoader(DocumentDataLoader):
    """Parse a Word file with python-docx, following the body in order.

    Each paragraph takes its kind from its Word style: Title, Heading 1 to 9
    or an outline level, Quote, Caption and HTML Preformatted. A paragraph
    with list numbering becomes a list item, ordered unless its numbering
    level draws bullets. Tables keep their rows, and a first row marked to
    repeat as a header makes the table a headed one.
    """

    SCHEMA: ClassVar[BaseSchema] = PythonDocxDocumentSchema
    SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({".docx"})
    DISPLAY_NAME = MultilingualString(
        en="python-docx",
        es="python-docx",
        pt="python-docx",
        de="python-docx",
        zh="python-docx",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Reads Word files (docx) with python-docx. Stores each paragraph "
            "and table in reading order, named after its Word style as a "
            "title, heading, list item, quote, caption or code, and can also "
            "store the embedded images and the page headers and footers."
            " [https://github.com/python-openxml/python-docx]"
            "(https://github.com/python-openxml/python-docx)"
        ),
        es=(
            "Lee archivos de Word (docx) con python-docx. Guarda cada párrafo "
            "y tabla en orden de lectura, nombrado según su estilo de Word "
            "como título, encabezado, elemento de lista, cita, leyenda o "
            "código, y también puede guardar las imágenes incrustadas y los "
            "encabezados y pies de página."
            " [https://github.com/python-openxml/python-docx]"
            "(https://github.com/python-openxml/python-docx)"
        ),
        pt=(
            "Lê arquivos do Word (docx) com python-docx. Guarda cada parágrafo "
            "e tabela em ordem de leitura, nomeado conforme seu estilo do Word "
            "como título, cabeçalho, item de lista, citação, legenda ou "
            "código, e também pode guardar as imagens incorporadas e os "
            "cabeçalhos e rodapés."
            " [https://github.com/python-openxml/python-docx]"
            "(https://github.com/python-openxml/python-docx)"
        ),
        de=(
            "Liest Word-Dateien (docx) mit python-docx. Speichert jeden Absatz "
            "und jede Tabelle in Lesereihenfolge, benannt nach ihrer "
            "Word-Formatvorlage als Titel, Überschrift, Listenelement, Zitat, "
            "Beschriftung oder Code, und kann auch die eingebetteten Bilder "
            "sowie die Kopf- und Fußzeilen speichern."
            " [https://github.com/python-openxml/python-docx]"
            "(https://github.com/python-openxml/python-docx)"
        ),
        zh=(
            "使用 python-docx 读取 Word 文件（docx）。按阅读顺序保存每个段落和"
            "表格，并按其 Word 样式命名为标题、章节标题、列表项、引用、题注或"
            "代码；还可保存嵌入的图像以及页眉和页脚。"
            "[https://github.com/python-openxml/python-docx]"
            "(https://github.com/python-openxml/python-docx)"
        ),
    )

    @staticmethod
    def _style_chain(paragraph: Any) -> List[Any]:
        """Return the style of a paragraph followed by the styles it is based on.

        Parameters
        ----------
        paragraph : docx.text.paragraph.Paragraph
            The paragraph.

        Returns
        -------
        List[Any]
            The paragraph style first, then each base style; empty when the
            paragraph has no style.
        """
        chain = []
        style = paragraph.style
        while style is not None and style not in chain:
            chain.append(style)
            style = style.base_style
        return chain

    @classmethod
    def _heading_level(cls, paragraph: Any, chain: List[Any]) -> Optional[int]:
        """Return the heading level of a paragraph, None when it is no heading.

        Parameters
        ----------
        paragraph : docx.text.paragraph.Paragraph
            The paragraph.
        chain : List[Any]
            Its style chain, as ``_style_chain`` returns it.

        Returns
        -------
        Optional[int]
            1 to 6 from a ``Heading N`` style or an outline level, deeper
            levels capped at 6.
        """
        for style in chain:
            name = (style.name or "").lower()
            if name.startswith("heading ") and name[8:].isdigit():
                return min(int(name[8:]), 6)
        for properties in [paragraph._p.pPr, *(style.element.pPr for style in chain)]:
            outline = None if properties is None else properties.outlineLvl
            if outline is not None and outline.val is not None and outline.val < 9:
                return min(outline.val + 1, 6)
        return None

    @staticmethod
    def _numbering(paragraph: Any, chain: List[Any]) -> Optional[Tuple[int, int]]:
        """Return the numbering id and level of a paragraph.

        Parameters
        ----------
        paragraph : docx.text.paragraph.Paragraph
            The paragraph.
        chain : List[Any]
            Its style chain, as ``_style_chain`` returns it.

        Returns
        -------
        Optional[Tuple[int, int]]
            ``(numId, ilvl)`` from the paragraph or its styles, None when it
            has no numbering or numbering 0, which turns it off.
        """
        num_id = None
        level = None
        for properties in [paragraph._p.pPr, *(style.element.pPr for style in chain)]:
            num_pr = None if properties is None else properties.numPr
            if num_pr is None:
                continue
            if num_id is None and num_pr.numId is not None:
                num_id = num_pr.numId.val
            if level is None and num_pr.ilvl is not None:
                level = num_pr.ilvl.val
        if not num_id:
            return None
        return num_id, level or 0

    @staticmethod
    def _is_ordered(numbering: Any, num_id: int, level: int) -> bool:
        """Tell whether a numbering level counts instead of drawing bullets.

        Parameters
        ----------
        numbering : docx.oxml.numbering.CT_Numbering or None
            The ``w:numbering`` element of the file.
        num_id : int
            The numbering id of the paragraph.
        level : int
            Its numbering level.

        Returns
        -------
        bool
            True unless the level format is ``bullet`` or ``none``.
        """
        if numbering is None:
            return False
        abstract = numbering.xpath(
            f'./w:num[@w:numId="{num_id}"]/w:abstractNumId/@w:val'
        )
        if not abstract:
            return False
        formats = numbering.xpath(
            f'./w:abstractNum[@w:abstractNumId="{abstract[0]}"]'
            f'/w:lvl[@w:ilvl="{level}"]/w:numFmt/@w:val'
        )
        return bool(formats) and formats[0] not in UNORDERED_FORMATS

    @staticmethod
    def _numbering_element(document: Any) -> Any:
        """Return the ``w:numbering`` element of a file, None when it has none."""
        from docx.opc.constants import RELATIONSHIP_TYPE

        try:
            part = document.part.part_related_by(RELATIONSHIP_TYPE.NUMBERING)
        except KeyError:
            return None
        return part.element

    def _paragraph_element(
        self, paragraph: Any, numbering: Any
    ) -> Tuple[str, Dict[str, Any]]:
        """Return the element kind and attributes of a paragraph.

        Parameters
        ----------
        paragraph : docx.text.paragraph.Paragraph
            The paragraph.
        numbering : lxml element or None
            The ``w:numbering`` element of the file.

        Returns
        -------
        Tuple[str, Dict[str, Any]]
            The kind and its attributes, ``paragraph`` when the style names
            nothing else.
        """
        chain = self._style_chain(paragraph)
        for style in chain:
            kind = STYLE_KINDS.get((style.name or "").lower())
            if kind is not None:
                return kind, {}
        level = self._heading_level(paragraph, chain)
        if level is not None:
            return "heading", {"level": level}
        list_numbering = self._numbering(paragraph, chain)
        if list_numbering is not None:
            num_id, depth = list_numbering
            return "list_item", {
                "ordered": self._is_ordered(numbering, num_id, depth),
                "depth": depth,
            }
        return "paragraph", {}

    def _paragraph_images(self, paragraph: Any) -> List[Tuple[str, bytes, str]]:
        """Return the images drawn inside a paragraph, skipping broken ones.

        Parameters
        ----------
        paragraph : docx.text.paragraph.Paragraph
            The paragraph.

        Returns
        -------
        List[Tuple[str, bytes, str]]
            ``(name, data, alt text)`` of each image, in document order.
        """
        from docx.oxml.ns import qn

        images = []
        for drawing in paragraph._p.xpath(".//w:drawing"):
            descriptions = drawing.xpath(".//wp:docPr/@descr")
            alt = descriptions[0] if descriptions else ""
            for blip in drawing.xpath(".//a:blip"):
                rel_id = blip.get(qn("r:embed"))
                part = paragraph.part.related_parts.get(rel_id) if rel_id else None
                blob = getattr(part, "blob", None)
                if not blob:
                    log.warning("python-docx found no image for relation %s", rel_id)
                    continue
                images.append((part.partname.filename, blob, alt))
        return images

    @staticmethod
    def _table_rows(table: Any) -> List[List[str]]:
        """Return the rows of a table as lists of cell text.

        Parameters
        ----------
        table : docx.table.Table
            The table.

        Returns
        -------
        List[List[str]]
            Each row as its cells' text; a merged cell repeats its text in
            every grid column it spans.
        """
        return [[cell.text for cell in row.cells] for row in table.rows]

    @staticmethod
    def _has_header_row(table: Any) -> bool:
        """Tell whether the first row of a table repeats as a header row."""
        rows = table._tbl.tr_lst
        return bool(rows) and bool(rows[0].xpath("./w:trPr/w:tblHeader"))

    def _body_items(
        self, document: Any, params: Dict[str, Any]
    ) -> List["DocumentItem"]:
        """Read the body of a file into document items, in reading order.

        Parameters
        ----------
        document : docx.document.Document
            The opened file.
        params : Dict[str, Any]
            Resolved parameters.

        Returns
        -------
        List[DocumentItem]
            Text items for paragraphs and tables, and image items after the
            paragraph that holds them when ``extract_images`` is True.
        """
        from docx.table import Table

        from DashAI.back.dataloaders.classes.dashai_document import DocumentItem
        from DashAI.back.types.dashai_image import DashAIImage
        from DashAI.back.types.value_types import Text

        numbering = self._numbering_element(document)
        items = []
        for block in document.iter_inner_content():
            if isinstance(block, Table):
                rows = self._table_rows(block)
                content = table_text(rows)
                if content.strip():
                    items.append(
                        DocumentItem(
                            type=Text,
                            content=content,
                            kind="table",
                            attrs={
                                "rows": rows,
                                "header": self._has_header_row(block),
                            },
                        )
                    )
                continue
            text = block.text.strip()
            if text:
                kind, attrs = self._paragraph_element(block, numbering)
                items.append(
                    DocumentItem(type=Text, content=text, kind=kind, attrs=attrs)
                )
            if params["extract_images"]:
                for name, data, alt in self._paragraph_images(block):
                    items.append(
                        DocumentItem(
                            type=DashAIImage,
                            content=self.web_image(data, name),
                            attrs={"alt": alt} if alt else {},
                        )
                    )
        return items

    @staticmethod
    def _section_texts(document: Any, part_name: str) -> List[str]:
        """Return the text of the headers or footers of every section.

        Parameters
        ----------
        document : docx.document.Document
            The opened file.
        part_name : str
            ``"header"`` or ``"footer"``.

        Returns
        -------
        List[str]
            The non blank paragraphs of each section's primary header or
            footer, skipping the ones linked to the previous section.
        """
        texts = []
        for section in document.sections:
            part = getattr(section, part_name)
            if part.is_linked_to_previous:
                continue
            texts.extend(
                paragraph.text.strip()
                for paragraph in part.paragraphs
                if paragraph.text.strip()
            )
        return texts

    def load_document(self, file_path: str, params: Dict[str, Any]) -> "DashAIDocument":
        """Parse a Word file with python-docx.

        Parameters
        ----------
        file_path : str
            Path of the docx file.
        params : Dict[str, Any]
            ``extract_images`` and ``include_headers_footers``; missing keys
            take the defaults.

        Returns
        -------
        DashAIDocument
            Text and image items in reading order, with ``page=None`` since
            a Word file has no fixed pages.

        Raises
        ------
        DocumentLoaderError
            If python-docx cannot read the file.
        """
        import docx

        from DashAI.back.dataloaders.classes.dashai_document import (
            DashAIDocument,
            DocumentItem,
        )
        from DashAI.back.types.value_types import Text

        resolved = self.resolve_params(params)
        try:
            document = docx.Document(file_path)
            items = self._body_items(document, resolved)
            if resolved["include_headers_footers"]:
                items = [
                    *(
                        DocumentItem(type=Text, content=text, kind="page_header")
                        for text in self._section_texts(document, "header")
                    ),
                    *items,
                    *(
                        DocumentItem(type=Text, content=text, kind="page_footer")
                        for text in self._section_texts(document, "footer")
                    ),
                ]
        except Exception as e:
            raise DocumentLoaderError(
                f"python-docx failed to read {file_path}: {e}"
            ) from e
        return DashAIDocument.from_items(
            items, metadata=self.build_metadata(file_path, resolved, None)
        )
