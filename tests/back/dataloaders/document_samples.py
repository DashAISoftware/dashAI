"""File samples for the document loader tests."""

import io
from pathlib import Path
from typing import List, Tuple

Line = Tuple[str, float, float]


def write_layout_pdf(path: Path, pages: List[List[Line]]) -> str:
    """Write a PDF placing each line at a font size and a vertical position.

    Parameters
    ----------
    path : pathlib.Path
        Destination file.
    pages : List[List[Line]]
        Per page, each line as ``(latin-1 text, font size, baseline y)``.

    Returns
    -------
    str
        The path written.
    """
    page_refs = [4 + 2 * index for index in range(len(pages))]
    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        f"<</Type/Pages/Kids[{kids}]/Count {len(pages)}>>".encode("latin-1"),
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    for ref, lines in zip(page_refs, pages, strict=True):
        stream = "\n".join(
            f"BT /F1 {size} Tf 72 {y} Td ({text}) Tj ET" for text, size, y in lines
        ).encode("latin-1")
        objects.append(
            (
                "<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                f"/Resources<</Font<</F1 3 0 R>>>>/Contents {ref + 1} 0 R>>"
            ).encode("latin-1")
        )
        objects.append(b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream))
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj" % number + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer<</Size %d/Root 1 0 R>>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF" % xref_pos
    path.write_bytes(bytes(out))
    return str(path)


HEADING_PAGES: List[List[Line]] = [
    [
        ("Introduction", 24, 700),
        ("First body line.", 12, 660),
        ("still the same block.", 12, 646),
        ("A second paragraph.", 12, 600),
    ],
    [
        ("Method", 24, 700),
        ("Body on page two.", 12, 660),
    ],
]
"""Two pages, each a 24pt heading over 12pt body text in three blocks."""


def write_text_pdf(path: Path, pages: List[str]) -> str:
    """Write a PDF with one Helvetica text line per page.

    Parameters
    ----------
    path : pathlib.Path
        Destination file.
    pages : List[str]
        Latin-1 text of each page; an empty string makes a page without text.

    Returns
    -------
    str
        The path written.
    """
    page_refs = [4 + 2 * index for index in range(len(pages))]
    kids = " ".join(f"{ref} 0 R" for ref in page_refs)
    objects = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        f"<</Type/Pages/Kids[{kids}]/Count {len(pages)}>>".encode("latin-1"),
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    for ref, text in zip(page_refs, pages, strict=True):
        stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode("latin-1")
        objects.append(
            (
                "<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
                f"/Resources<</Font<</F1 3 0 R>>>>/Contents {ref + 1} 0 R>>"
            ).encode("latin-1")
        )
        objects.append(b"<</Length %d>>stream\n%s\nendstream" % (len(stream), stream))
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj" % number + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer<</Size %d/Root 1 0 R>>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF" % xref_pos
    path.write_bytes(bytes(out))
    return str(path)


def image_pdf_bytes() -> bytes:
    """Return a one page PDF holding a single 8x8 red JPEG and no text.

    Returns
    -------
    bytes
        The PDF file content.
    """
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PDF")
    return buffer.getvalue()


def write_mixed_pdf(path: Path) -> str:
    """Write a two page PDF: "Alpha" plus an image on page 1, "Bravo" on page 2.

    Parameters
    ----------
    path : pathlib.Path
        Destination file.

    Returns
    -------
    str
        The path written.
    """
    from pypdf import PdfReader, PdfWriter

    text_path = path.with_name(f"{path.stem}_text.pdf")
    write_text_pdf(text_path, ["Alpha", "Bravo"])
    writer = PdfWriter(clone_from=str(text_path))
    writer.pages[0].merge_page(PdfReader(io.BytesIO(image_pdf_bytes())).pages[0])
    writer.write(str(path))
    return str(path)


def png_bytes() -> bytes:
    """Return a 4x4 red PNG.

    Returns
    -------
    bytes
        The PNG file content.
    """
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def write_docx(path: Path) -> str:
    """Write a Word file with one paragraph of each style the loaders name.

    The body reads: a Title, a Heading 1, a paragraph, a bullet with a
    nested bullet at numbering level 1, a numbered item, a Heading 2, a
    table whose first row repeats as a header, a picture with alt text, a
    Caption, a Quote and a closing paragraph. The page header says "Top"
    and the page footer says "Bottom".

    Parameters
    ----------
    path : pathlib.Path
        Destination file.

    Returns
    -------
    str
        The path written.
    """
    from docx import Document
    from docx.oxml import OxmlElement

    document = Document()
    document.sections[0].header.paragraphs[0].text = "Top"
    document.sections[0].footer.paragraphs[0].text = "Bottom"
    document.add_paragraph("Report", style="Title")
    document.add_heading("Introduction", level=1)
    document.add_paragraph("Body text.")
    document.add_paragraph("Bullet", style="List Bullet")
    nested = document.add_paragraph("Nested bullet", style="List Bullet")
    nested._p.get_or_add_pPr().get_or_add_numPr().get_or_add_ilvl().val = 1
    document.add_paragraph("Numbered", style="List Number")
    document.add_heading("Results", level=2)
    table = document.add_table(rows=2, cols=2)
    for row, values in zip(table.rows, [["Name", "Score"], ["Ada", ""]], strict=True):
        for cell, value in zip(row.cells, values, strict=True):
            cell.text = value
    table.rows[0]._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
    document.add_picture(io.BytesIO(png_bytes()))
    document.inline_shapes[0]._inline.docPr.set("descr", "A red square")
    document.add_paragraph("Figure 1", style="Caption")
    document.add_paragraph("Quoted words.", style="Quote")
    document.add_paragraph("The end.")
    document.save(str(path))
    return str(path)
