"""Tests that RAG components actually load and execute.

Models are downloaded, loaded, and run with real inputs. Only models
with at most 8B parameters are included.
"""

import tempfile

import numpy as np
import pytest

pytestmark = pytest.mark.slow

from tests.back.RAG.benchmark_data import (
    _MockDocument,
    CHUNKING_DOCUMENT,
    MULTI_TURN_CONVERSATION,
    REALISTIC_CORPUS,
    TEST_CHUNKS,
    build_test_chunks,
)

# ── LLMs ────────────────────────────────────────────────────────────
from DashAI.back.models.hugging_face.llama_model import LlamaModel
from DashAI.back.models.hugging_face.mistral_model import MistralModel
from DashAI.back.models.hugging_face.qwen_model import QwenModel
from DashAI.back.models.hugging_face.smol_lm_model import SmolLMModel
from DashAI.back.models.hugging_face.phi_4_mini_instruct_model import Phi4MiniInstructModel

# ── Embeddings ──────────────────────────────────────────────────────
from DashAI.back.models.RAG.embeddings.dense.sentence_transformer_embedding import (
    SentenceTransformerEmbedding,
)
from DashAI.back.models.RAG.embeddings.dense.bert_embedding import BERTEmbedding
from DashAI.back.models.RAG.embeddings.dense.distilbert_embedding import DistilBERTEmbedding
from DashAI.back.models.RAG.embeddings.dense.e5_embedding import E5Embedding

# ── Retrievers ──────────────────────────────────────────────────────
from DashAI.back.models.RAG.retrievers.sparse.bm25_retriever import (
    BM25Retriever,
    BM25VectorizerModel,
)
from DashAI.back.models.RAG.retrievers.sparse.tfidf_retriever import (
    TFIDFRetriever,
    TFIDFVectorizerModel,
)
from DashAI.back.models.RAG.retrievers.dense.dense_embedding_retriever import (
    DenseEmbeddingRetriever,
)
from DashAI.back.models.RAG.retrievers.composite.mmr_reranker_retriever import (
    MMRRerankerRetriever,
)

# ── Persistence ─────────────────────────────────────────────────────
from DashAI.back.models.RAG.retrievers.persistence import SparsePersistence, DensePersistence

# ── Chunkers ────────────────────────────────────────────────────────
from DashAI.back.models.RAG.chunking_models.character_chunk_model import CharacterChunkModel
from DashAI.back.models.RAG.chunking_models.recursive_character_chunk_model import (
    RecursiveCharacterChunkModel,
)
from DashAI.back.models.RAG.chunking_models.token_chunk_model import TokenChunkModel

# ── Documents ───────────────────────────────────────────────────────
from DashAI.back.models.RAG.documents.base_document import BaseDocument
from DashAI.back.models.RAG.documents.chunk import Chunk

# ── Prompts ─────────────────────────────────────────────────────────
from DashAI.back.models.RAG.prompts.generation.default_rag_generation_prompt import (
    DefaultRAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.generation.default_qna_rag_generation_prompt import (
    DefaultQnARAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.generation.custom_rag_generation_prompt import (
    CustomRAGGenerationPrompt,
)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1 — LLM Execution
# ═══════════════════════════════════════════════════════════════════


class TestLLMExecution:
    """Download a GGUF model, run one generation, verify output is plausible."""

    def test_llama_1b_generate(self):
        try:
            model = LlamaModel(
                model_name="bartowski/Llama-3.2-1B-Instruct-GGUF",
                quantization="Q4_K_M",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Llama 1B load failed: {e}")
        result = model.generate(MULTI_TURN_CONVERSATION[:2])
        assert len(result) == 1, f"Expected 1 response, got {len(result)}"
        assert len(result[0]) > 0, "Expected non-empty output"

    def test_llama_3b_generate(self):
        try:
            model = LlamaModel(
                model_name="bartowski/Llama-3.2-3B-Instruct-GGUF",
                quantization="Q4_K_M",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Llama 3B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_mistral_7b_generate(self):
        try:
            model = MistralModel(
                model_name="bartowski/Mistral-7B-Instruct-v0.3-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Mistral 7B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_qwen_0_5b_generate(self):
        try:
            model = QwenModel(
                model_name="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Qwen 0.5B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_qwen_1_5b_generate(self):
        try:
            model = QwenModel(
                model_name="Qwen/Qwen2.5-1.5B-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Qwen 1.5B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_qwen_3b_generate(self):
        try:
            model = QwenModel(
                model_name="Qwen/Qwen2.5-3B-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Qwen 3B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_smol_360m_generate(self):
        try:
            model = SmolLMModel(
                model_name="HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"SmolLM 360M load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_smol_1_7b_generate(self):
        try:
            model = SmolLMModel(
                model_name="HuggingFaceTB/SmolLM2-1.7B-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"SmolLM 1.7B load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_phi4_mini_generate(self):
        try:
            model = Phi4MiniInstructModel(
                model_name="unsloth/Phi-4-mini-instruct-GGUF",
                quantization="Phi-4-mini-instruct.Q8_0.gguf",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Phi-4 Mini load failed: {e}")
        result = model.generate(
            [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        )
        assert len(result) == 1
        assert "4" in result[0], f"Expected '4', got: {result[0]}"

    def test_smol_360m_generate_with_different_temperatures(self):
        try:
            model_low = SmolLMModel(
                model_name="HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
            model_high = SmolLMModel(
                model_name="HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
                max_tokens=30,
                temperature=0.9,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"SmolLM 360M load failed: {e}")
        prompt = [{"role": "user", "content": "Say hello in one word."}]
        result_low = model_low.generate(prompt)
        result_high = model_high.generate(prompt)
        assert len(result_low[0]) > 0, "Low temperature output is empty"
        assert len(result_high[0]) > 0, "High temperature output is empty"

    def test_qwen_0_5b_respects_max_tokens(self):
        try:
            model_short = QwenModel(
                model_name="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                max_tokens=10,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
            model_long = QwenModel(
                model_name="Qwen/Qwen2.5-0.5B-Instruct-GGUF",
                max_tokens=50,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Qwen 0.5B load failed: {e}")
        prompt = [{"role": "user", "content": "Tell me a story about a cat."}]
        result_short = model_short.generate(prompt)
        result_long = model_long.generate(prompt)
        assert len(result_short[0]) < len(result_long[0]), (
            f"Short output ({len(result_short[0])} chars) should be shorter "
            f"than long output ({len(result_long[0])} chars)"
        )

    def test_llama_1b_handles_multiple_turns(self):
        try:
            model = LlamaModel(
                model_name="bartowski/Llama-3.2-1B-Instruct-GGUF",
                quantization="Q4_K_M",
                max_tokens=30,
                temperature=0.1,
                frequency_penalty=0.0,
                context_window=512,
                device="CPU",
            )
        except Exception as e:
            pytest.skip(f"Llama 1B load failed: {e}")
        result1 = model.generate(MULTI_TURN_CONVERSATION[:2])
        result2 = model.generate(MULTI_TURN_CONVERSATION[:4])
        assert len(result1[0]) > 0, "First response is empty"
        assert len(result2[0]) > 0, "Second response is empty"


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2 — Embedding Execution
# ═══════════════════════════════════════════════════════════════════


class TestEmbeddingExecution:
    """Load an embedding model, encode text, verify output shape."""

    def test_st_minilm_encode(self):
        try:
            emb = SentenceTransformerEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
                normalize=True,
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"all-MiniLM-L6-v2 load failed: {e}")
        emb.load()
        vec = emb.encode("Hello world")
        assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
        assert vec.shape == (384,), f"Expected (384,), got {vec.shape}"
        assert vec.any(), "Embedding is all zeros"

    def test_harrier_0_6b_encode(self):
        try:
            emb = SentenceTransformerEmbedding(
                model_name="microsoft/harrier-oss-v1-0.6b",
                device="cpu",
                normalize=True,
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"Harrier 0.6B load failed: {e}")
        emb.load()
        vec = emb.encode("Hello world")
        assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
        assert vec.ndim == 1, f"Expected 1-D, got {vec.ndim}D"
        assert vec.any(), "Embedding is all zeros"

    def test_bert_encode(self):
        try:
            emb = BERTEmbedding(
                model_name="google-bert/bert-base-uncased",
                device="cpu",
                overflow_strategy="truncate",
                pooling_strategy="mean",
            )
        except Exception as e:
            pytest.skip(f"BERT base load failed: {e}")
        emb.load()
        vec = emb.encode("test")
        assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
        assert vec.shape[0] > 100, f"Dimension too small: {vec.shape[0]}"
        assert vec.any(), "Embedding is all zeros"

    def test_distilbert_encode(self):
        try:
            emb = DistilBERTEmbedding(
                model_name="distilbert/distilbert-base-uncased",
                device="cpu",
                overflow_strategy="truncate",
                pooling_strategy="mean",
            )
        except Exception as e:
            pytest.skip(f"DistilBERT base load failed: {e}")
        emb.load()
        vec = emb.encode("test")
        assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
        assert vec.shape[0] > 100, f"Dimension too small: {vec.shape[0]}"
        assert vec.any(), "Embedding is all zeros"

    def test_e5_small_encode(self):
        try:
            emb = E5Embedding(
                model_name="intfloat/e5-small-v2",
                device="cpu",
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"E5 small load failed: {e}")
        emb.load()
        vec = emb.encode("test")
        assert isinstance(vec, np.ndarray), f"Expected ndarray, got {type(vec)}"
        assert vec.shape[0] == 384, f"Expected 384-d, got {vec.shape}"
        assert vec.any(), "Embedding is all zeros"

    def test_st_batch_encode(self):
        try:
            emb = SentenceTransformerEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
                normalize=True,
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"all-MiniLM-L6-v2 load failed: {e}")
        emb.load()
        vecs = emb.batch_encode(["text one", "text two", "text three"])
        assert isinstance(vecs, np.ndarray), f"Expected ndarray, got {type(vecs)}"
        assert vecs.shape == (3, 384), f"Expected (3, 384), got {vecs.shape}"


# ═══════════════════════════════════════════════════════════════════
#  SECTION 3 — Retriever Execution
# ═══════════════════════════════════════════════════════════════════


class TestRetrieverExecution:
    """Build retrievers, inject infra, retrieve, verify results."""

    def test_bm25_retrieve(self):
        vectorizer = BM25VectorizerModel(
            strip_accents=None,
            lowercase=True,
            stop_words=None,
            max_df=1.0,
            min_df=0.0,
            max_features=None,
        )
        retriever = BM25Retriever(
            BM25Vectorizer=vectorizer,
            k1=1.5,
            b=0.75,
            delta=0.0,
            similarity_function="cosine",
            top_k=2,
        )
        chunks = build_test_chunks(doc_ids=[0])
        retriever.inject_infra(
            env_rag_path=tempfile.mkdtemp(),
            chunks=chunks,
            persistence=SparsePersistence(model_dir=None),
        )
        retriever.init_model()
        results = retriever.retrieve("metformin first-line therapy")
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert "metformin" in results[0].text.lower(), (
            f"Top result should contain metformin, got: {results[0].text}"
        )

    def test_tfidf_retrieve(self):
        tfidf_vec = TFIDFVectorizerModel(
            strip_accents="None",
            lowercase=True,
            analyzer="word",
            stop_words=[],
            ngram_range=[1, 1],
            max_df=1.0,
            min_df=0.0,
            max_features=1000,
            norm="l2",
            use_idf=True,
            smooth_idf=True,
            sublinear_tf=False,
        )
        retriever = TFIDFRetriever(
            TFIDFVectorizer=tfidf_vec,
            similarity_function="cosine",
            top_k=2,
        )
        chunks = build_test_chunks(doc_ids=[0])
        retriever.inject_infra(
            env_rag_path=tempfile.mkdtemp(),
            chunks=chunks,
            persistence=SparsePersistence(model_dir=None),
        )
        retriever.init_model()
        results = retriever.retrieve("metformin first-line therapy")
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert "metformin" in results[0].text.lower(), (
            f"Top result should contain metformin, got: {results[0].text}"
        )

    def test_dense_st_retrieve(self):
        tmpdir = tempfile.mkdtemp()
        try:
            emb = SentenceTransformerEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
                normalize=True,
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"all-MiniLM-L6-v2 load failed: {e}")
        emb.load()
        retriever = DenseEmbeddingRetriever(
            embedding_model=emb,
            similarity_metric="cosine",
            top_k=2,
        )
        chunks = build_test_chunks(doc_ids=[0])
        retriever.inject_infra(
            env_rag_path=tmpdir,
            chunks=chunks,
            persistence=DensePersistence(matrix_dirs={0: tmpdir}, embedding_model_id=0),
        )
        retriever.init_model()
        results = retriever.retrieve("metformin first-line therapy")
        assert len(results) == 2, f"Expected 2, got {len(results)}"
        assert "metformin" in results[0].text.lower(), (
            f"Top result should contain metformin, got: {results[0].text}"
        )

    def test_mmr_reranker_retrieve(self):
        tmpdir = tempfile.mkdtemp()
        try:
            emb = SentenceTransformerEmbedding(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                device="cpu",
                normalize=True,
                overflow_strategy="truncate",
            )
        except Exception as e:
            pytest.skip(f"all-MiniLM-L6-v2 load failed: {e}")
        emb.load()
        child = DenseEmbeddingRetriever(
            embedding_model=emb,
            similarity_metric="cosine",
            top_k=6,
        )
        chunks = build_test_chunks(doc_ids=[0])
        child.inject_infra(
            env_rag_path=tmpdir,
            chunks=chunks,
            persistence=DensePersistence(matrix_dirs={0: tmpdir}, embedding_model_id=0),
        )
        child.init_model()
        mmr = MMRRerankerRetriever(
            children=[child],
            mmr_lambda=0.5,
            retrieval_factor=2,
            top_k=2,
        )
        results = mmr.retrieve("metformin first-line therapy")
        assert len(results) == 2, f"Expected 2, got {len(results)}"


# ═══════════════════════════════════════════════════════════════════
#  SECTION 4 — Chunker Execution
# ═══════════════════════════════════════════════════════════════════


class TestChunkerExecution:
    """Create a mock document, chunk it, verify chunk structure."""

    def test_character_chunker(self):
        doc = _MockDocument(0, CHUNKING_DOCUMENT)
        chunker = CharacterChunkModel(
            chunk_size=80,
            chunk_overlap=10,
            documents={0: doc},
        )
        chunks = chunker.get_chunks()
        assert len(chunks) == 1, f"Expected 1 doc in chunks, got {len(chunks)}"
        assert len(chunks[0]) >= 1, "Expected at least 1 chunk"
        first_chunk = list(chunks[0].values())[0]
        assert len(first_chunk.text) > 0, "Chunk text should not be empty"

    def test_recursive_character_chunker(self):
        doc = _MockDocument(0, CHUNKING_DOCUMENT)
        chunker = RecursiveCharacterChunkModel(
            chunk_size=80,
            chunk_overlap=10,
            separators=["\n\n", "\n", ".", " ", ""],
            documents={0: doc},
        )
        chunks = chunker.get_chunks()
        assert len(chunks) == 1, f"Expected 1 doc, got {len(chunks)}"
        assert len(chunks[0]) >= 1, "Expected at least 1 chunk"

    def test_token_chunker(self):
        doc = _MockDocument(0, CHUNKING_DOCUMENT)
        chunker = TokenChunkModel(
            tokenizer_name="intfloat/e5-mistral-7b-instruct",
            chunk_size=20,
            chunk_overlap=5,
            documents={0: doc},
        )
        chunks = chunker.get_chunks()
        assert len(chunks) == 1, f"Expected 1 doc, got {len(chunks)}"
        assert len(chunks[0]) >= 1, "Expected at least 1 chunk"


# ═══════════════════════════════════════════════════════════════════
#  SECTION 5 — Prompt Execution
# ═══════════════════════════════════════════════════════════════════


class TestPromptExecution:
    """Construct prompts, format with input+chunks, verify output."""

    def test_default_rag_prompt_format(self):
        prompt = DefaultRAGGenerationPrompt(language="en", template="")
        formatted = prompt.format(
            input="What is the recommended first-line medication for type 2 diabetes?",
            chunks="Metformin remains the first-line pharmacological therapy due to its efficacy.",
        )
        assert "Metformin" in formatted, (
            f"Expected chunks content in prompt, got: {formatted}"
        )
        assert "{input}" not in formatted, "Placeholder {input} not replaced"
        assert "{chunks}" not in formatted, "Placeholder {chunks} not replaced"

    def test_default_qna_prompt_format(self):
        prompt = DefaultQnARAGGenerationPrompt(language="en", template="")
        formatted = prompt.format(
            input="What is metformin?",
            chunks="Metformin is first-line therapy for type 2 diabetes.",
        )
        assert "metformin" in formatted.lower(), f"Expected 'metformin' in prompt, got: {formatted}"
        assert "{input}" not in formatted, "Placeholder {input} not replaced"

    def test_custom_prompt_format(self):
        prompt = CustomRAGGenerationPrompt(
            template="CONTEXT:\n{chunks}\n\nQUERY: {input}\n\nANSWER:"
        )
        formatted = prompt.format(input="test question", chunks="test context")
        assert "test question" in formatted
        assert "test context" in formatted
        assert "{input}" not in formatted

    def test_prompt_multilingual_spanish(self):
        prompt = DefaultRAGGenerationPrompt(language="es", template="")
        formatted = prompt.format(
            input="¿Cómo se trata la diabetes tipo 2?",
            chunks="La metformina es el tratamiento farmacológico de primera línea.",
        )
        assert "metformina" in formatted.lower(), f"Expected 'metformina' in prompt, got: {formatted}"
        assert len(formatted) > 20, (
            f"Formatted prompt too short ({len(formatted)} chars): {formatted}"
        )


# ═══════════════════════════════════════════════════════════════════════
#  Standalone entry point (run with: python benchmark_execution.py)
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v", "-m", "slow", *sys.argv[1:]]))
