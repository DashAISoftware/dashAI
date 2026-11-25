import fnmatch
from types import SimpleNamespace

import pytest
import torch
import transformers

from DashAI.back.converters.document.surya_ocr import SuryaOCRConverter

PROMPT = (
    "OCR this image to HTML. Each block is a div with data-label and data-bbox "
    "(x0 y0 x1 y1, normalized 0-1000)."
)

# Surya 2.5's compact output for a page with a header and a table: a block header
# is one label and four coordinates, <|box|> prefixes a tag with a data-bbox, and
# </td>, </tr> and </div> are left out. The model ends the page with <|im_end|>.
COMPACT_PAGE = (
    "<|Page-Header|><|71|><|33|><|143|><|45|><p>Quarterly report</p>"
    "<|Table|><|71|><|60|><|900|><|200|>"
    "<table><tr><|box|><|10|><|10|><|20|><|20|><td>A<td>B &amp; C"
    "<tr><td>D<td>E</table>"
    "<|im_end|>"
)

# Files in datalab-to/surya-ocr-2.5 (name -> bytes), as listed on the Hub.
HUB_FILES = {
    ".gitattributes": 3413,
    "LICENSE": 14726,
    "README.md": 33127,
    "chat_template.jinja": 2872,
    "config.json": 2695,
    "generation_config.json": 132,
    "model.safetensors": 1378772208,
    "preprocessor_config.json": 390,
    "processor_config.json": 1191,
    "static/datalab-logo.png": 6169,
    "static/docs/multilingual.md": 5021,
    "static/images/corporate.png": 386925,
    "tokenizer.json": 4228747,
    "tokenizer_config.json": 775,
    "video_preprocessor_config.json": 385,
}


class _Batch(dict):
    def to(self, device):
        return self


class _FakeProcessor:
    def __init__(self, decoded):
        self.decoded = decoded
        self.messages = None

    def apply_chat_template(self, messages, **kwargs):
        self.messages = messages
        return _Batch(input_ids=torch.tensor([[1, 2]]))

    def decode(self, tokens, **kwargs):
        return self.decoded


class _FakeModel:
    def __init__(self):
        self.generate_kwargs = None

    def generate(self, **kwargs):
        self.generate_kwargs = kwargs
        return torch.tensor([[1, 2, 3]])


class _Loaded:
    def to(self, device):
        return self

    def eval(self):
        return self


def _read_page(monkeypatch, decoded, **options):
    converter = SuryaOCRConverter(**options)
    processor, model = _FakeProcessor(decoded), _FakeModel()
    monkeypatch.setattr(converter, "pretrained", lambda: (processor, model))
    return converter.read_images([object()]), processor, model


def test_compact_page_becomes_plain_text(monkeypatch):
    texts, processor, _ = _read_page(monkeypatch, COMPACT_PAGE)

    assert texts == ["Quarterly report\nA B & C\nD E"]
    assert "<|" not in texts[0]
    assert "Table" not in texts[0]
    assert processor.messages[0]["content"][1]["text"] == PROMPT


def test_terminal_marker_is_not_stored_as_text(monkeypatch):
    texts, _, _ = _read_page(monkeypatch, "A line of text.<|im_end|>\n")

    assert texts == ["A line of text."]


def test_every_terminal_marker_is_stripped(monkeypatch):
    texts, _, _ = _read_page(monkeypatch, "A line<|im_end|><|endoftext|>")

    assert texts == ["A line"]


def test_block_labels_separate_text_without_html_paragraphs(monkeypatch):
    decoded = (
        "<|Text|><|1|><|2|><|3|><|4|>First block"
        "<|Text|><|5|><|6|><|7|><|8|>Second block<|im_end|>"
    )

    texts, _, _ = _read_page(monkeypatch, decoded)

    assert texts == ["First block\nSecond block"]


@pytest.mark.parametrize("decoded", ["<|im_end|>", "<|im_end|>\n", "<|endoftext|>", ""])
def test_a_page_with_only_an_end_marker_yields_no_text(monkeypatch, decoded):
    texts, _, _ = _read_page(monkeypatch, decoded)

    assert texts == [""]


def test_a_truncated_page_fails_instead_of_saving_partial_text(monkeypatch):
    partial = "<|Text|><|1|><|2|><|3|><|4|><p>The first half of the"

    with pytest.raises(ValueError, match="128 tokens"):
        _read_page(monkeypatch, partial, max_tokens=128)


def test_a_repetition_loop_fails_instead_of_becoming_document_text(monkeypatch):
    repetitive = "<|Text|><|1|><|2|><|3|><|4|><p>" + "same text " * 100

    with pytest.raises(ValueError, match="repetition loop"):
        _read_page(monkeypatch, repetitive + "<|im_end|>")


def test_repeated_numeric_table_rows_are_not_a_repetition_loop(monkeypatch):
    rows = "".join("<tr><td>N/A<td>N/A" for _ in range(7))
    decoded = f"<|Table|><|1|><|2|><|3|><|4|><table>{rows}</table><|im_end|>"

    texts, _, _ = _read_page(monkeypatch, decoded)

    assert texts[0].count("N/A") == 14


def test_an_inline_box_marker_does_not_split_the_line(monkeypatch):
    decoded = (
        "<|Text|><|1|><|2|><|3|><|4|><p>Hello"
        "<|box|><|10|><|10|><|20|><|20|><img/>world</p><|im_end|>"
    )

    texts, _, _ = _read_page(monkeypatch, decoded)

    assert texts == ["Hello world"]


def test_the_page_token_budget_is_passed_to_generate(monkeypatch):
    _, _, model = _read_page(monkeypatch, COMPACT_PAGE, max_tokens=256)

    assert model.generate_kwargs["max_new_tokens"] == 256
    assert model.generate_kwargs["do_sample"] is False
    assert SuryaOCRConverter().max_tokens == 12288


def test_pages_are_capped_at_surya_full_page_pixels(monkeypatch):
    calls = {}

    def recorder(name, result):
        def load(source, **kwargs):
            calls[name] = kwargs
            return result

        return load

    monkeypatch.setattr(
        transformers.models.auto.image_processing_auto,
        "AutoImageProcessor",
        SimpleNamespace(from_pretrained=recorder("image", "image-processor")),
    )
    monkeypatch.setattr(
        transformers.models.auto.processing_auto,
        "AutoProcessor",
        SimpleNamespace(from_pretrained=recorder("processor", _Loaded())),
    )
    monkeypatch.setattr(
        transformers.models.auto.modeling_auto,
        "AutoModelForImageTextToText",
        SimpleNamespace(from_pretrained=recorder("model", _Loaded())),
    )

    SuryaOCRConverter(device="CPU").load_pretrained("/models/surya")

    assert calls["image"]["size"] == {
        "shortest_edge": 3136,
        "longest_edge": 6291456,
    }
    assert calls["processor"]["image_processor"] == "image-processor"


def test_download_fetches_only_the_files_transformers_loads():
    ((repo, kind, patterns),) = SuryaOCRConverter.hf_repos()
    selected = {
        name
        for name in HUB_FILES
        if any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
    }

    assert (repo, kind) == ("datalab-to/surya-ocr-2.5", "model")
    assert selected == {
        "chat_template.jinja",
        "config.json",
        "generation_config.json",
        "model.safetensors",
        "preprocessor_config.json",
        "processor_config.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "video_preprocessor_config.json",
    }
    total = sum(HUB_FILES[name] for name in selected)
    assert total == SuryaOCRConverter.DOWNLOAD_SIZE_BYTES
    assert SuryaOCRConverter.get_metadata()["requires_download"] is True


def test_an_undownloaded_model_is_not_fetched_from_the_hub(monkeypatch):
    monkeypatch.setattr(
        SuryaOCRConverter, "is_downloaded", classmethod(lambda cls: False)
    )

    with pytest.raises(RuntimeError, match="not downloaded"):
        SuryaOCRConverter()._pretrained_source()


def test_saved_model_dir_does_not_require_the_component_download(monkeypatch):
    monkeypatch.setattr(
        SuryaOCRConverter, "is_downloaded", classmethod(lambda cls: False)
    )

    source = SuryaOCRConverter()._pretrained_source("/saved/surya")

    assert source == "/saved/surya"
