"""Unit tests for the LLM filter prompt family.

Verifies the anchor's placeholder contract, the language-driven default
templates, custom-template validation, the optional-line semantics and the
numbered-chunk rendering the filter retriever relies on.
"""

from __future__ import annotations

import json

import pytest

from DashAI.back.models.RAG.exceptions import RAGPromptTemplateError
from DashAI.back.models.RAG.prompts.evaluation import (
    CustomLLMFilterPrompt,
    DefaultLLMFilterPrompt,
    LLMFilterPrompt,
)
from DashAI.back.models.RAG.prompts.evaluation import (
    default_llm_filter_prompt as filter_mod,
)

OPTIONAL_PLACEHOLDERS = [
    "{topk}",
    "{documents.names}",
    "{documents.description}",
]

DOCUMENTS = [
    {
        "document_id": 1,
        "name": "alpha.pdf",
        "chunks": 4,
        "pages": 2,
    }
]

CHUNKS = [
    {"document_id": 1, "position": 0, "text": "first chunk"},
    {"document_id": 2, "position": 3, "text": "second chunk"},
]


# ===================================================================
# placeholder declarations
# ===================================================================


class TestPlaceholderDeclarations:
    """Class-level placeholder attributes match the fixed contract."""

    def test_anchor_contract(self):
        assert LLMFilterPrompt.required_placeholders == ["{input}", "{chunks}"]
        assert LLMFilterPrompt.optional_placeholders == OPTIONAL_PLACEHOLDERS

    def test_default_prompt_inherits_contract(self):
        assert DefaultLLMFilterPrompt.required_placeholders == ["{input}", "{chunks}"]
        assert DefaultLLMFilterPrompt.optional_placeholders == OPTIONAL_PLACEHOLDERS

    def test_custom_prompt_inherits_contract(self):
        assert CustomLLMFilterPrompt.required_placeholders == ["{input}", "{chunks}"]
        assert CustomLLMFilterPrompt.optional_placeholders == OPTIONAL_PLACEHOLDERS


# ===================================================================
# default templates
# ===================================================================


class TestDefaultTemplates:
    """Default templates validate and expose the selection contract."""

    @pytest.mark.parametrize("lang", ["en", "es", "pt"])
    def test_templates_validate(self, lang):
        assert DefaultLLMFilterPrompt.validate_template(filter_mod.TEMPLATES[lang])

    def test_templates_expose_function_call_contract(self):
        for template in filter_mod.TEMPLATES.values():
            assert "select_best_chunks" in template
            assert "selected_chunks" in template
            for placeholder in (
                "{input}",
                "{chunks}",
                "{topk}",
                "{documents.names}",
                "{documents.description}",
            ):
                assert placeholder in template
            assert "```" not in template

    @pytest.mark.parametrize(
        ("lang", "phrase"),
        [
            ("en", "no markdown fences and no extra text"),
            ("es", "sin bloques de código y sin texto adicional"),
            ("pt", "sem blocos de código e sem texto adicional"),
        ],
    )
    def test_templates_forbid_fences_and_extra_text(self, lang, phrase):
        assert phrase in filter_mod.TEMPLATES[lang]

    @pytest.mark.parametrize(
        ("lang", "function_phrase", "fallback_phrases"),
        [
            (
                "en",
                "Respond by calling the function select_best_chunks",
                ("If function calling is available", "Otherwise", "In either case"),
            ),
            (
                "es",
                "Responde llamando a la función select_best_chunks",
                (
                    "Si la llamada a funciones está disponible",
                    "De lo contrario",
                    "En cualquier caso",
                ),
            ),
            (
                "pt",
                "Responda chamando a função select_best_chunks",
                (
                    "Se a chamada de função estiver disponível",
                    "Caso contrário",
                    "Em qualquer caso",
                ),
            ),
        ],
    )
    def test_templates_always_call_the_function(
        self, lang, function_phrase, fallback_phrases
    ):
        """The template always instructs function calling, with no text fallback."""
        template = filter_mod.TEMPLATES[lang]
        assert function_phrase in template
        assert "select_best_chunks" in template
        assert "selected_chunks" in template
        for fallback_phrase in fallback_phrases:
            assert fallback_phrase not in template

    def test_templates_describe_one_based_unique_best_first(self):
        for template in filter_mod.TEMPLATES.values():
            lowered = template.lower()
            assert (
                "best first" in lowered or "primero" in lowered or "primeiro" in lowered
            )

    @pytest.mark.parametrize(
        ("lang", "phrase"),
        [
            ("en", "Invalid selections are rejected"),
            ("es", "Las selecciones inválidas se rechazan"),
            ("pt", "Seleções inválidas são rejeitadas"),
        ],
    )
    def test_templates_state_invalid_selections_are_rejected(self, lang, phrase):
        """The model is told that invalid selections are retried, not applied."""
        assert phrase in filter_mod.TEMPLATES[lang]


# ===================================================================
# format rendering
# ===================================================================


class TestFormatRendering:
    """``format`` substitutes placeholders and drops optional lines."""

    def test_replaces_required_and_optional(self):
        prompt = DefaultLLMFilterPrompt(language="en")
        rendered = prompt.format(
            input="What is DashAI?",
            chunks=CHUNKS,
            top_k=3,
            documents=DOCUMENTS,
        )

        assert "What is DashAI?" in rendered
        assert "[1] (document_id=1, position=0) first chunk" in rendered
        assert "[2] (document_id=2, position=3) second chunk" in rendered
        assert "at most 3 best chunks" in rendered
        assert "alpha.pdf" in rendered
        assert '"document_id": 1' in rendered
        for token in OPTIONAL_PLACEHOLDERS:
            assert token not in rendered

    def test_rendered_numbering_is_one_based(self):
        prompt = DefaultLLMFilterPrompt(language="en")
        rendered = prompt.format(input="Q?", chunks=CHUNKS, top_k=2)

        assert "[1]" in rendered
        assert "[2]" in rendered
        assert "[0]" not in rendered

    def test_optional_lines_dropped_when_none(self):
        prompt = DefaultLLMFilterPrompt(language="en")
        rendered = prompt.format(input="Q?", chunks="only chunk")

        for token in OPTIONAL_PLACEHOLDERS:
            assert token not in rendered
        assert "Documents:" not in rendered
        assert "Document description" not in rendered
        assert "at most" not in rendered

    def test_dict_values_render_as_indented_json(self):
        prompt = DefaultLLMFilterPrompt(language="en")
        rendered = prompt.format(
            input="Q?",
            chunks="chunk",
            top_k=2,
            documents=[{"document_id": 2, "name": "beta.pdf"}],
        )

        assert (
            json.dumps(
                [{"document_id": 2, "name": "beta.pdf"}],
                ensure_ascii=False,
                indent=2,
            )
            in rendered
        )
        assert "beta.pdf" in rendered

    def test_missing_document_name_falls_back(self):
        prompt = DefaultLLMFilterPrompt(language="en")
        rendered = prompt.format(
            input="Q?",
            chunks="chunk",
            documents=[{"document_id": 7, "name": None, "chunks": 1, "pages": 0}],
        )

        assert "document 7" in rendered

    def test_malformed_chunk_payload_raises(self):
        prompt = CustomLLMFilterPrompt(template="{input}|{chunks}")

        with pytest.raises(RAGPromptTemplateError, match="missing required keys"):
            prompt.format(input="q", chunks=[{"document_id": 1, "position": 0}])

    def test_non_mapping_chunk_payload_raises(self):
        prompt = CustomLLMFilterPrompt(template="{input}|{chunks}")

        with pytest.raises(RAGPromptTemplateError, match="must be a mapping"):
            prompt.format(input="q", chunks=["not a mapping"])

    def test_truncated_chunk_text_gets_an_ellipsis(self):
        prompt = CustomLLMFilterPrompt(template="{input}|{chunks}")

        rendered = prompt.format(
            input="q",
            chunks=[{"document_id": 1, "position": 0, "text": "x" * 500}],
        )

        assert "x" * 400 + "..." in rendered

    def test_preformatted_chunks_are_kept_verbatim(self):
        prompt = CustomLLMFilterPrompt(template="{input}||{chunks}")
        rendered = prompt.format(input="q", chunks="[9] already rendered")
        assert rendered == "q||[9] already rendered"

    def test_default_prompt_picks_template_by_language(self):
        for lang in ("en", "es", "pt"):
            prompt = DefaultLLMFilterPrompt(language=lang)
            assert prompt.template == filter_mod.TEMPLATES[lang]

    def test_unknown_language_raises(self):
        with pytest.raises(RAGPromptTemplateError):
            DefaultLLMFilterPrompt(language="klingon")


# ===================================================================
# custom templates
# ===================================================================


class TestCustomTemplates:
    """Custom prompts validate their template on construction."""

    def test_custom_missing_required_placeholder_raises(self):
        with pytest.raises(RAGPromptTemplateError):
            CustomLLMFilterPrompt(template="no placeholders here")

    def test_custom_missing_chunks_raises(self):
        with pytest.raises(RAGPromptTemplateError):
            CustomLLMFilterPrompt(template="only {input} present")

    def test_custom_valid_renders(self):
        prompt = CustomLLMFilterPrompt(template="{input} || {chunks}")
        assert prompt.format(input="a", chunks="b") == "a || b"

    def test_custom_allows_absent_optional(self):
        prompt = CustomLLMFilterPrompt(template="{input} || {chunks}")
        rendered = prompt.format(input="a", chunks="b", top_k=None)
        assert rendered == "a || b"

    def test_custom_renders_document_names_and_topk(self):
        prompt = CustomLLMFilterPrompt(
            template="{input}|{chunks}|{documents.names}|{topk}"
        )
        rendered = prompt.format(
            input="a",
            chunks="b",
            documents=[
                {"document_id": 1, "name": "alpha"},
                {"document_id": 2, "name": "beta"},
            ],
            top_k=7,
        )
        assert rendered == "a|b|alpha, beta|7"

    def test_custom_prompt_has_multilingual_ui_metadata(self):
        """The prompt selector must not fall back to the base display name."""
        assert CustomLLMFilterPrompt.DISPLAY_NAME != "Base RAG Prompt"
        assert CustomLLMFilterPrompt.DESCRIPTION != "Base class for RAG prompts."
        for language in ("en", "es", "pt", "de", "zh"):
            assert getattr(CustomLLMFilterPrompt.DISPLAY_NAME, language)
            assert getattr(CustomLLMFilterPrompt.DESCRIPTION, language)
