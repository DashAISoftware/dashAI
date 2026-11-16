"""Read document images with Surya's document OCR model."""

import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

from DashAI.back.converters.document.image_reader import ImageReader, keep_image_field
from DashAI.back.converters.hugging_face.pretrained_tool import (
    TORCH_DEVICE_CPU,
    TORCH_DEVICE_CUDA_PREFIX,
    device_field,
)
from DashAI.back.core.schema_fields import int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.utils import DEVICE_PLACEHOLDER

#: Whole-page prompt Surya was trained with (``HIGH_ACCURACY_BBOX_PROMPT``).
OCR_PROMPT = (
    "OCR this image to HTML. Each block is a div with data-label and data-bbox "
    "(x0 y0 x1 y1, normalized 0-1000)."
)
#: Pixel bounds of a page image, the same as Surya's full-page reference.
MIN_PAGE_PIXELS = 3136
MAX_PAGE_PIXELS = 6291456
PAGE_SIZE: Dict[str, int] = {
    "shortest_edge": MIN_PAGE_PIXELS,
    "longest_edge": MAX_PAGE_PIXELS,
}
#: Tokens that end a generated page, as the decoder spells them out.
TERMINAL_MARKERS = ("<|im_end|>", "<|im_end!>", "<|endoftext|>")
#: Every special token: compact block labels, their coordinates and ``<|box|>``.
SPECIAL_TOKEN_RE = re.compile(r"<\|[^<>|]*\|>")
#: Surya's top-level block labels; only these start a new block.
BLOCK_LABELS = (
    "Caption",
    "Footnote",
    "Equation-Block",
    "List-Group",
    "Page-Header",
    "Page-Footer",
    "Image",
    "Section-Header",
    "Table",
    "Text",
    "Complex-Block",
    "Code-Block",
    "Form",
    "Table-Of-Contents",
    "Figure",
    "Chemical-Block",
    "Diagram",
    "Bibliography",
    "Blank-Page",
    "Picture",
)
BLOCK_LABEL_RE = re.compile(
    r"<\|(?:%s)\|>" % "|".join(re.escape(label) for label in BLOCK_LABELS)
)
#: Files ``from_pretrained`` reads: weights, configs, tokenizer, processor and
#: chat template. The ``*.json`` glob matches only top-level files in this repo.
HF_ALLOW_PATTERNS: List[str] = ["*.json", "*.jinja", "*.safetensors"]
_REPEAT_BASE_MAX = 4
_REPEAT_WINDOW = 500
_REPEAT_SCALING = 3.0


class SuryaOCRSchema(BaseSchema):
    """Schema for the Surya OCR converter."""

    keep_image: keep_image_field()  # type: ignore
    max_tokens: schema_field(
        int_field(ge=128, le=16384),
        12288,
        description=MultilingualString(
            en=(
                "Maximum generated tokens per page. Raise for dense pages; a page "
                "that reaches the limit fails instead of saving partial text."
            ),
            es=(
                "Máximo de tokens generados por página. Auméntalo para páginas "
                "densas; una página que lo alcance falla en lugar de guardar texto "
                "incompleto."
            ),
            pt=(
                "Máximo de tokens gerados por página. Aumente para páginas densas; "
                "uma página que atingir o limite falha em vez de salvar texto "
                "incompleto."
            ),
            de=(
                "Maximal generierte Tokens pro Seite. Für dichte Seiten erhöhen; "
                "eine Seite am Limit schlägt fehl, statt unvollständigen Text zu "
                "speichern."
            ),
            zh=(
                "每页生成的最大词元数。内容密集时可调高；达到上限的页面会报错，"
                "而不是保存不完整的文本。"
            ),
        ),
    )  # type: ignore
    device: device_field()  # type: ignore


class _HTMLTextExtractor(HTMLParser):
    """Extract normalized text from a page's HTML."""

    _LINE_BREAK_TAGS = {
        "br",
        "div",
        "h1",
        "h2",
        "h3",
        "h4",
        "li",
        "p",
        "tr",
    }
    _CELL_TAGS = {
        "td",
        "th",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: List[str] = []

    def handle_data(self, data: str) -> None:
        """Append a text segment from the parsed HTML."""
        self.parts.append(data)

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        """Preserve block and cell boundaries while ignoring HTML attributes.

        Parameters
        ----------
        tag : str
            Lowercase HTML tag name.
        attrs : Any
            HTML attributes, unused by plain-text extraction.
        """
        if tag in self._LINE_BREAK_TAGS:
            self.parts.append("\n")
        elif tag in self._CELL_TAGS:
            self.parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        """Preserve closing block and cell boundaries.

        Parameters
        ----------
        tag : str
            Lowercase HTML tag name.
        """
        if tag in self._LINE_BREAK_TAGS:
            self.parts.append("\n")
        elif tag in self._CELL_TAGS:
            self.parts.append(" ")

    def text(self) -> str:
        """Return normalized lines while preserving paragraphs and table rows.

        Returns
        -------
        str
            Non-empty text lines joined by newlines.
        """
        lines = []
        for line in "".join(self.parts).splitlines():
            if line.strip():
                lines.append(" ".join(line.split()))
        return "\n".join(lines)


def _strip_terminal_marker(raw: str) -> Tuple[str, bool]:
    """Remove every trailing end-of-sequence marker from decoded page output.

    Parameters
    ----------
    raw : str
        The decoded output, with special tokens kept.

    Returns
    -------
    Tuple[str, bool]
        The output without its trailing markers, and whether the page finished.
        Output without any marker was cut off by the token budget.
    """
    text = raw.rstrip()
    if not text:
        return "", True
    finished = False
    for _ in range(len(TERMINAL_MARKERS) * 2):
        for marker in TERMINAL_MARKERS:
            if text.endswith(marker):
                text = text[: -len(marker)].rstrip()
                finished = True
                break
        else:
            break
    if not finished:
        return raw, False
    return text, True


def _compact_to_text(value: str) -> str:
    """Turn one page of compact Surya output into plain text.

    Parameters
    ----------
    value : str
        The page output without its terminal marker.

    Returns
    -------
    str
        The text in reading order, preserving paragraph and table row boundaries.
    """
    # A block label is a visual block boundary; its coordinates and ``<|box|>``
    # are metadata that become spaces.
    text = BLOCK_LABEL_RE.sub("\n", value)
    parser = _HTMLTextExtractor()
    parser.feed(SPECIAL_TOKEN_RE.sub(" ", text))
    parser.close()
    return parser.text()


def _has_repeated_suffix(text: str) -> bool:
    """Detect a repeated suffix pattern in generated page text.

    Parameters
    ----------
    text : str
        Plain text decoded from one OCR page.

    Returns
    -------
    bool
        Whether the text ends in a degenerate repeated sequence.
    """
    for length in range(1, _REPEAT_WINDOW // 2 + 1):
        candidate = text[-length:]
        if not any(character.isalnum() for character in candidate):
            continue
        max_repeats = int(_REPEAT_BASE_MAX * (1 + _REPEAT_SCALING / length))
        repeats = 0
        position = len(text) - length
        while position >= 0 and text[position : position + length] == candidate:
            repeats += 1
            position -= length
        if repeats > max_repeats:
            return True
    return False


def _page_text(raw: str, max_tokens: int) -> str:
    """Return the plain text of one decoded page.

    Parameters
    ----------
    raw : str
        The decoded output, with special tokens kept.
    max_tokens : int
        The token budget the page was generated with, for the error message.

    Returns
    -------
    str
        The page text, empty when the page has no text.

    Raises
    ------
    ValueError
        If the output has no end marker, so the page was cut off.
    """
    body, finished = _strip_terminal_marker(raw)
    if not finished:
        raise ValueError(
            f"Surya OCR did not finish the page within {max_tokens} tokens. "
            "Raise the maximum generated tokens per page to read it in full."
        )
    # Check the compact output, as Surya does: flattening removes the per-block
    # label/coordinate tokens that break periodicity in table rows.
    if _has_repeated_suffix(body):
        raise ValueError("Surya OCR produced a repetition loop instead of page text.")
    return _compact_to_text(body)


class SuryaOCRConverter(ImageReader):
    """Extract multilingual document text using Surya OCR.

    Runs Surya's Qwen3.5-based OCR checkpoint directly with Transformers and
    PyTorch. The model weights use DashAI's normal component download flow; no
    external inference server or executable is needed.
    """

    SCHEMA = SuryaOCRSchema
    MODEL_NAME = "datalab-to/surya-ocr-2.5"
    DOWNLOAD_SIZE_BYTES = 1_383_009_395
    OUTPUT_KIND = "paragraph"
    DISPLAY_NAME = MultilingualString(
        en="Surya OCR",
        es="OCR con Surya",
        pt="OCR com Surya",
        de="Surya OCR",
        zh="Surya OCR",
    )
    DESCRIPTION = MultilingualString(
        en=(
            "Reads multilingual text and document structure from images with "
            "Surya locally with Transformers and PyTorch; the model is downloaded "
            "as a DashAI component."
        ),
        es=(
            "Lee texto multilingüe y la estructura de documentos en imágenes "
            "con Surya localmente mediante Transformers y PyTorch; el modelo se "
            "descarga como componente de DashAI."
        ),
        pt=(
            "Lê texto multilíngue e a estrutura de documentos em imagens com "
            "Surya localmente com Transformers e PyTorch; o modelo é baixado "
            "como componente do DashAI."
        ),
        de=(
            "Liest mehrsprachigen Text und Dokumentstruktur aus Bildern mit "
            "Surya lokal mit Transformers und PyTorch; das Modell wird als "
            "DashAI-Komponente heruntergeladen."
        ),
        zh=(
            "使用 Transformers 和 PyTorch 在本地运行 Surya，"
            "识别图像中的多语言文本和文档结构；"
            "模型通过 DashAI 组件下载。"
        ),
    )

    def __init__(
        self,
        keep_image: bool = True,
        max_tokens: int = 12288,
        device: str = DEVICE_PLACEHOLDER,
    ) -> None:
        """Store OCR options without loading the model.

        Parameters
        ----------
        keep_image : bool
            Keep each source image in the document.
        max_tokens : int
            Maximum generated tokens per page; incomplete output is rejected.
        device : str
            CPU or a CUDA device label supported by the installed PyTorch build.
        """
        super().__init__()
        self.keep_source = keep_image
        self.max_tokens = max_tokens
        self.setup_device(device)

    @classmethod
    def hf_repos(cls) -> List[Tuple[str, str, List[str]]]:
        """Return the Surya repo and only the files Transformers loads.

        Returns
        -------
        List[Tuple[str, str, List[str]]]
            The repo id, its type and the allowed file patterns.
        """
        return [(cls.MODEL_NAME, "model", list(HF_ALLOW_PATTERNS))]

    def _pretrained_source(self, pretrained_dir: Optional[str] = None) -> str:
        """Return the downloaded model folder; never fall back to the Hub.

        Parameters
        ----------
        pretrained_dir : str, optional
            Directory of a previously saved run, if any.

        Returns
        -------
        str
            A path or repo id accepted by ``from_pretrained``.

        Raises
        ------
        RuntimeError
            If the model has not been downloaded. Some job paths do not check
            the download gate, so this keeps the load from fetching the weights
            outside DashAI's component storage.
        """
        if pretrained_dir is not None:
            return super()._pretrained_source(pretrained_dir)
        if not self.is_downloaded():
            raise RuntimeError(
                f"{self.MODEL_NAME} is not downloaded. Download Surya OCR before use."
            )
        return super()._pretrained_source(pretrained_dir)

    def load_pretrained(self, source: str) -> Tuple[Any, Any]:
        """Load Surya's Transformers processor and vision-language model.

        Parameters
        ----------
        source : str
            The downloaded model folder.

        Returns
        -------
        Tuple[Any, Any]
            The processor and the model on ``self.device``, in eval mode.

        Raises
        ------
        OSError
            If the downloaded Transformers model files are missing or invalid.
        """
        import torch
        from transformers import (
            AutoImageProcessor,
            AutoModelForImageTextToText,
            AutoProcessor,
        )

        image_processor = AutoImageProcessor.from_pretrained(
            source, size=dict(PAGE_SIZE)
        )
        processor = AutoProcessor.from_pretrained(
            source, image_processor=image_processor
        )
        if self.device == TORCH_DEVICE_CPU:
            dtype = torch.float32
        elif (
            self.device.startswith(TORCH_DEVICE_CUDA_PREFIX)
            and torch.cuda.is_bf16_supported()
        ):
            dtype = torch.bfloat16
        else:
            dtype = torch.float16
        model = AutoModelForImageTextToText.from_pretrained(source, dtype=dtype)
        return processor, model.to(self.device).eval()

    def read_images(self, images: List[Any]) -> List[str]:
        """OCR a batch of RGB PIL images and return plain text per image.

        Parameters
        ----------
        images : List[PIL.Image.Image]
            RGB page images.

        Returns
        -------
        List[str]
            The text of each page, empty when the page has none.

        Raises
        ------
        RuntimeError
            If the Surya component has not been downloaded.
        ValueError
            If a page is truncated or degenerates into a repetition loop.
        """
        processor, model = self.pretrained()
        return [self._read_page(processor, model, image) for image in images]

    def _read_page(self, processor: Any, model: Any, image: Any) -> str:
        """Generate the OCR output of one page and return its plain text.

        Parameters
        ----------
        processor : Any
            The Transformers processor.
        model : Any
            The loaded vision-language model.
        image : PIL.Image.Image
            One RGB page image.

        Returns
        -------
        str
            The page text.

        Raises
        ------
        ValueError
            If the page output is truncated or degenerates into a repetition loop.
        """
        import torch

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ]
        inputs = processor.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
        ).to(self.device)
        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                do_sample=False,
                max_new_tokens=self.max_tokens,
            )
        prompt_length = inputs["input_ids"].shape[-1]
        raw = processor.decode(
            generated[0, prompt_length:],
            skip_special_tokens=False,
            clean_up_tokenization_spaces=False,
        )
        return _page_text(raw, self.max_tokens)
