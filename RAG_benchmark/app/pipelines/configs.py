"""Thesis pipeline configurations for the RAG benchmark suite.

Each configuration corresponds to a row in the thesis comparison table.
Theses rows are re-based onto the *current* DashAI component registry:

* ``pub1`` — Medical Fitness: RecursiveCharacterChunkModel (1000/100),
  DenseEmbeddingRetriever over OpenAIEmbedding
  (``text-embedding-ada-002``), cosine, top_k=10, Llama 3.2 3B Instruct.
* ``pub2`` — EHR Summarization: CharacterChunkModel (600/40),
  MMRRerankerRetriever over DenseEmbeddingRetriever with MiniLM,
  cosine, top 20/60, Llama 3.2 3B Instruct.
* ``pub3`` — Case Study: same retrieval/chunking as ``pub1`` with the
  1B Llama generator.
* ``pub4a`` — RAGChecker Dense: TokenChunkModel (e5-mistral tokenizer,
  300/60), DenseEmbeddingRetriever over E5MistralGGUFEmbedding
  (the Q5_K_M quantized ``intfloat/e5-mistral-7b-instruct`` GGUF),
  cosine, top_k=20, Llama 3.2 3B Instruct.
* ``pub4b`` — RAGChecker Sparse: TokenChunkModel (300/60), BM25Retriever
  over a BagOfWordsConverter vectorizer, cosine, top_k=20,
  Llama 3.2 3B Instruct.
* ``pub5a`` — Query Rewriting (BM25 + cross-encoder): TokenChunkModel
  (e5-mistral tokenizer, 300/60), ``BM25Retriever`` over a
  ``BagOfWordsConverter`` vectorizer retrieving 10 candidates, re-ranked by
  ``SentenceTransformerCrossEncoderRetriever``
  (``cross-encoder/mmarco-mMiniLMv2-L12-H384-v1``) down to 5 chunks, plus an
  ``LLMQueryRewriter`` query-transformation stage (Qwen 2.5 7B Instruct).
  Generates with Llama 3.2 3B Instruct.
* ``pub5b`` — Query Decomposition (MiniLM + cross-encoder): the same
  cross-encoder re-ranking over a ``DenseEmbeddingRetriever`` with
  ``AllMiniLML6V2Embedding`` retrieving 10 candidates, plus an
  ``LLMQueryDecomposer`` query-transformation stage (Qwen 2.5 7B Instruct).
  Generates with Llama 3.2 3B Instruct.
* ``pub5c`` — Query Expansion (TF-IDF + cross-encoder): the same cross-encoder
  re-ranking over a ``TFIDFRetriever`` (``TFIDFConverter`` vectorizer)
  retrieving 10 candidates, plus an ``LLMQueryExpander`` query-transformation
  stage (Qwen 2.5 7B Instruct). Generates with Llama 3.2 3B Instruct.

Migration notes
---------------
* ``pub1``/``pub3`` are back on OpenAI ``text-embedding-ada-002`` through the
  ``OpenAIEmbedding`` converter. The model is selected by its ``model_name``
  parameter (so the same class also serves ``text-embedding-3-small`` /
  ``text-embedding-3-large``) and the credential is read from the
  ``OPENAI_API_KEY`` environment variable when the config is built. No key is
  ever written to a results file: the pipeline runner and the component
  benchmark both redact/keep it empty in the logged config.
* ``pub2`` keeps ``AllMiniLML6V2Embedding``: it wraps the same
  ``sentence-transformers/all-MiniLM-L6-v2`` checkpoint the thesis used, so it
  is the semantic equivalent of the former ``SentenceTransformerEmbedding``.
* ``pub4a`` uses ``E5MistralGGUFEmbedding``, the quantized Q5_K_M GGUF build of
  ``intfloat/e5-mistral-7b-instruct``. The fp16 checkpoint is *not* used. The
  same checkpoint name survives as the ``TokenChunkModel`` tokenizer.
* ``pub4b`` BM25 uses ``BagOfWordsConverter``: it is the same CountVectorizer
  the former ``BM25VectorizerModel`` fitted, so it is the semantic equivalent
  of the removed vectorizer model.
* ``pub5a``/``pub5b``/``pub5c`` add a ``SentenceTransformerCrossEncoderRetriever``
  re-ranking stage on top of a 10-candidate pool. The cross-encoder is **not**
  a downloadable DashAI component (the checkpoint name is a parameter, not a
  class), so the pipeline pre-flight checks the Hugging Face cache for
  ``cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`` itself and fetches it before
  the first turn. Their query-transformation LLM is ``Qwen25_7BInstruct``
  (Qwen 2.5 7B Instruct GGUF), replacing the former 1.5B model: a 7B model is
  far more reliable at following the "return a JSON list of N queries"
  instruction, so fewer transformations fall back to the raw message.
* ``LlamaModel`` was replaced by checkpoint-specific GGUF classes. The
  generation component now declares its own GGUF repo/quantization, so the
  ``model_name``/``quantization`` params were removed and the shared
  ``GGUFTextGenerationSchema`` fields (max_tokens, temperature,
  frequency_penalty, context_window, device) are used instead.
* Sessions no longer accept ``documents`` inside ``parameters``; the
  runner creates the session and attaches the corpus afterwards. The
  ``doc_ids`` argument is kept for signature compatibility but ignored.
"""

from __future__ import annotations

from typing import Any, Dict, List

from DashAI.back.models.RAG.prompts.generation.default_RAG_generation_prompt import (
    TEMPLATES as RAG_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_decomposition_prompt import (  # noqa: E501
    TEMPLATES as DECOMPOSITION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_expansion_prompt import (  # noqa: E501
    TEMPLATES as EXPANSION_PROMPT_TEMPLATES,
)
from DashAI.back.models.RAG.prompts.transformation.default_query_rewriting_prompt import (  # noqa: E501
    TEMPLATES as REWRITING_PROMPT_TEMPLATES,
)

#: Registered checkpoint-specific generation components (GGUF).
GEN_LLAMA_3B = "Llama32_3BInstruct"
GEN_LLAMA_1B = "Llama32_1BInstruct"
GEN_QWEN_7B = "Qwen25_7BInstruct"

#: Registered embedding converter components used by the dense retrievers.
EMB_OPENAI = "OpenAIEmbedding"
EMB_MINILM_L6_V2 = "AllMiniLML6V2Embedding"
EMB_E5_MISTRAL_GGUF = "E5MistralGGUFEmbedding"

#: Remote embedding model the thesis used for ``pub1``/``pub3``.
OPENAI_EMBEDDING_MODEL = "text-embedding-ada-002"

#: Environment variable that supplies the OpenAI credential. The pipeline
#: configs resolve it when they are built (the pipeline pre-flight fails when
#: it is empty) and the embedding benchmark reads it again at execution time.
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"

#: Hugging Face checkpoint kept only as the ``TokenChunkModel`` tokenizer.
#: ``E5MistralGGUFEmbedding`` embeds with the quantized GGUF build of it.
E5_MISTRAL_TOKENIZER = "intfloat/e5-mistral-7b-instruct"

#: Registered components used by the sparse (BM25 / TF-IDF) pipelines.
RETRIEVER_BM25 = "BM25Retriever"
RETRIEVER_TFIDF = "TFIDFRetriever"
RETRIEVER_DENSE = "DenseEmbeddingRetriever"
RETRIEVER_CROSS_ENCODER = "SentenceTransformerCrossEncoderRetriever"
VECTORIZER_BAG_OF_WORDS = "BagOfWordsConverter"
VECTORIZER_TFIDF = "TFIDFConverter"

#: Cross-encoder checkpoint the publication 5 pipelines re-rank with. It is a
#: retriever *parameter* (not a downloadable component class), so the pipeline
#: pre-flight has to gate its Hugging Face cache explicitly.
CROSS_ENCODER_MMARCO_MULTILINGUAL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

#: Number of candidates the initial retriever returns before re-ranking (K1).
PUB5_RETRIEVER_TOP_K = 10

#: Number of chunks the cross-encoder hands to the generator (K2).
PUB5_RERANK_TOP_K = 5

#: Size of the e5-mistral token windows every RAGChecker pipeline chunks into.
RAGCHECKER_CHUNK_SIZE = 300
RAGCHECKER_CHUNK_OVERLAP = 60

#: Language every pipeline prompt is rendered in.
PROMPT_LANGUAGE = "en"

#: Conversation turns the query transformers receive before the current one.
HISTORY_WINDOW = 2

#: Sub-query cap of the decomposition stage.
MAX_SUBQUERIES = 4

#: Query budget of the expansion stage.
N_QUERIES = 3

RECURSIVE_SEPARATORS = ["\n\n", "\n", ".", " ", ""]


def _generation_model(
    component: str,
    *,
    max_tokens: int = 1024,
    context_window: int = 8192,
) -> Dict[str, Any]:
    """Build a GGUF text-generation component ref.

    Parameters
    ----------
    component : str
        Name of the registered GGUF checkpoint class.
    max_tokens : int
        Maximum number of new tokens per response.
    context_window : int
        Total token budget for a single forward pass.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": component,
        "params": {
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": context_window,
            "device": "CPU",
        },
    }


def _rag_generation_prompt() -> Dict[str, Any]:
    """Build the default RAG generation prompt component ref (English)."""
    return {
        "component": "DefaultRAGGenerationPrompt",
        "params": {
            "language": PROMPT_LANGUAGE,
            "template": RAG_PROMPT_TEMPLATES[PROMPT_LANGUAGE],
        },
    }


def _minilm_embedding() -> Dict[str, Any]:
    """Build the registered MiniLM embedding converter component ref (CPU).

    ``AllMiniLML6V2Embedding`` wraps ``sentence-transformers/all-MiniLM-L6-v2``,
    the same checkpoint the thesis used, so it is the semantic equivalent of the
    former ``SentenceTransformerEmbedding``. The checkpoint name is baked into
    the component, so the params only carry the encoding options from
    ``TextEmbeddingSchema``.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": EMB_MINILM_L6_V2,
        "params": {
            "device": "CPU",
            "batch_size": 32,
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    }


def _openai_embedding() -> Dict[str, Any]:
    """Build the OpenAI embedding converter component ref (CPU).

    ``OpenAIEmbedding`` calls a remote embedding endpoint, so the checkpoint is
    selected by ``model_name`` instead of being baked into the class. The
    credential is read from ``OPENAI_API_KEY`` at encode time; the config
    carries an empty key so the secret never reaches the session database,
    the API payloads or the results files.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": EMB_OPENAI,
        "params": {
            "model_name": OPENAI_EMBEDDING_MODEL,
            "api_key": "",
            "device": "CPU",
            "batch_size": 32,
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    }


def _e5_mistral_gguf_embedding() -> Dict[str, Any]:
    """Build the quantized e5-mistral embedding converter component ref (CPU).

    ``E5MistralGGUFEmbedding`` wraps the Q5_K_M GGUF build of
    ``intfloat/e5-mistral-7b-instruct``; the repo and quantization are declared
    by the class, so the params only carry the encoding options from
    ``TextEmbeddingSchema``.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": EMB_E5_MISTRAL_GGUF,
        "params": {
            "device": "CPU",
            "batch_size": 32,
            "normalize": True,
            "overflow_strategy": "truncate",
        },
    }


def _token_chunking_model() -> Dict[str, Any]:
    """Build the RAGChecker token chunker ref (e5-mistral tokenizer, 300/60).

    The tokenizer name is only used to split text into token windows; the
    ``E5MistralGGUFEmbedding`` converter is the *only* place the e5-mistral
    checkpoint is used for vectorisation.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": "TokenChunkModel",
        "params": {
            "tokenizer_name": E5_MISTRAL_TOKENIZER,
            "chunk_size": RAGCHECKER_CHUNK_SIZE,
            "chunk_overlap": RAGCHECKER_CHUNK_OVERLAP,
        },
    }


def _bag_of_words_vectorizer() -> Dict[str, Any]:
    """Build the explicit ``BagOfWordsConverter`` vectorizer ref.

    The schema fills nothing in, so every option is passed explicitly: word
    analyzer, lowercase, 1-grams, ``min_df=0.0`` and ``max_df=1.0``.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": VECTORIZER_BAG_OF_WORDS,
        "params": {
            "max_features": None,
            "lowercase": True,
            "strip_accents": None,
            "analyzer": "word",
            "stop_words": None,
            "custom_stop_words": None,
            "lower_bound_ngrams": 1,
            "upper_bound_ngrams": 1,
            "min_df": 0.0,
            "max_df": 1.0,
        },
    }


def _tfidf_vectorizer() -> Dict[str, Any]:
    """Build the ``TFIDFConverter`` vectorizer ref at its schema placeholders.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` reference for the RAG pipeline.
    """
    return {
        "component": VECTORIZER_TFIDF,
        "params": {
            "max_features": 1000,
            "lowercase": True,
            "strip_accents": None,
            "analyzer": "word",
            "stop_words": None,
            "custom_stop_words": None,
            "lower_bound_ngrams": 1,
            "upper_bound_ngrams": 1,
            "min_df": 0.0,
            "max_df": 1.0,
            "norm": "l2",
            "use_idf": True,
            "smooth_idf": True,
            "sublinear_tf": False,
        },
    }


def _pub1_like_parameters(generation_component: str) -> Dict[str, Any]:
    """Build the retrieval/chunking parameters shared by ``pub1`` and ``pub3``."""
    return {
        "chunking_model": {
            "component": "RecursiveCharacterChunkModel",
            "params": {
                "chunk_size": 1000,
                "chunk_overlap": 100,
                "separators": RECURSIVE_SEPARATORS,
            },
        },
        "retriever_model": {
            "component": "DenseEmbeddingRetriever",
            "params": {
                "embedding_model": _openai_embedding(),
                "similarity_metric": "cosine",
                "top_k": 10,
            },
        },
        "generation_model": _generation_model(generation_component),
        "prompt": _rag_generation_prompt(),
    }


def get_pub1_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 1: Medical Fitness — OpenAI ada-002 embeddings, cosine, top_k=10,
    RecursiveCharacter (1000/100), Llama 3.2 3B Instruct.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; the corpus is attached to the session after
        creation, so the value is currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 1 - Medical Fitness",
        "description": None,
        "parameters": _pub1_like_parameters(GEN_LLAMA_3B),
    }


def get_pub2_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 2: EHR Summarization — MiniLM embeddings, MMR,
    top_k=20/60, CharacterChunk (600/40), Llama 3.2 3B Instruct.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 2 - EHR Summarization",
        "description": None,
        "parameters": {
            "chunking_model": {
                "component": "CharacterChunkModel",
                "params": {"chunk_size": 600, "chunk_overlap": 40},
            },
            "retriever_model": {
                "component": "MMRRerankerRetriever",
                "params": {
                    "mmr_lambda": 0.5,
                    "top_k": 20,
                    "children": [
                        {
                            "component": "DenseEmbeddingRetriever",
                            "params": {
                                "embedding_model": _minilm_embedding(),
                                "similarity_metric": "cosine",
                                "top_k": 60,
                            },
                        }
                    ],
                },
            },
            "generation_model": _generation_model(GEN_LLAMA_3B),
            "prompt": _rag_generation_prompt(),
        },
    }


def get_pub3_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 3: Case Study — same as Pub 1 with Llama 3.2 1B Instruct.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 3 - Case Study",
        "description": None,
        "parameters": _pub1_like_parameters(GEN_LLAMA_1B),
    }


def get_pub4a_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 4a: RAGChecker Dense — e5-mistral GGUF embeddings, cosine,
    top_k=20, TokenChunk (300/60, e5-mistral tokenizer), Llama 3.2 3B Instruct.

    Embedding uses the registered ``E5MistralGGUFEmbedding`` converter, the
    quantized Q5_K_M GGUF build of ``intfloat/e5-mistral-7b-instruct`` (the
    fp16 checkpoint is not used). ``device`` and ``overflow_strategy`` are the
    memory-safety settings of ``TextEmbeddingSchema``.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 4a - RAGChecker Dense",
        "description": None,
        "parameters": {
            "chunking_model": {
                "component": "TokenChunkModel",
                "params": {
                    "tokenizer_name": E5_MISTRAL_TOKENIZER,
                    "chunk_size": 300,
                    "chunk_overlap": 60,
                },
            },
            "retriever_model": {
                "component": "DenseEmbeddingRetriever",
                "params": {
                    "embedding_model": _e5_mistral_gguf_embedding(),
                    "similarity_metric": "cosine",
                    "top_k": 20,
                },
            },
            "generation_model": _generation_model(GEN_LLAMA_3B),
            "prompt": _rag_generation_prompt(),
        },
    }


def _pub4b_parameters() -> Dict[str, Any]:
    """Build the RAGChecker sparse parameters for pub4b.

    The tokenizer name below is only used to split text into tokens for
    chunking; the retrieval side is BM25 over a ``BagOfWordsConverter``
    vectorizer.
    """
    return {
        "chunking_model": _token_chunking_model(),
        "retriever_model": {
            "component": RETRIEVER_BM25,
            "params": {
                "vectorizer": _bag_of_words_vectorizer(),
                "similarity_function": "cosine",
                "top_k": 20,
                "k1": 1.5,
                "b": 0.75,
                "delta": 0.0,
            },
        },
        "generation_model": _generation_model(GEN_LLAMA_3B),
        "prompt": _rag_generation_prompt(),
    }


def get_pub4b_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 4b: RAGChecker Sparse — BM25, cosine, top_k=20, TokenChunk
    (300/60), Llama 3.2 3B Instruct.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 4b - RAGChecker Sparse",
        "description": None,
        "parameters": _pub4b_parameters(),
    }


def _bm25_candidate_retriever() -> Dict[str, Any]:
    """Build the BM25 candidate pool the pub5a re-ranker narrows.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` retriever reference with ``top_k`` = K1.
    """
    return {
        "component": RETRIEVER_BM25,
        "params": {
            "vectorizer": _bag_of_words_vectorizer(),
            "similarity_function": "cosine",
            "top_k": PUB5_RETRIEVER_TOP_K,
            "k1": 1.5,
            "b": 0.75,
            "delta": 0.0,
        },
    }


def _tfidf_candidate_retriever() -> Dict[str, Any]:
    """Build the TF-IDF candidate pool the pub5c re-ranker narrows.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` retriever reference with ``top_k`` = K1.
    """
    return {
        "component": RETRIEVER_TFIDF,
        "params": {
            "vectorizer": _tfidf_vectorizer(),
            "similarity_function": "cosine",
            "top_k": PUB5_RETRIEVER_TOP_K,
        },
    }


def _minilm_candidate_retriever() -> Dict[str, Any]:
    """Build the MiniLM dense candidate pool the pub5b re-ranker narrows.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` retriever reference with ``top_k`` = K1.
    """
    return {
        "component": RETRIEVER_DENSE,
        "params": {
            "embedding_model": _minilm_embedding(),
            "similarity_metric": "cosine",
            "top_k": PUB5_RETRIEVER_TOP_K,
        },
    }


def _cross_encoder_reranker(candidate_retriever: Dict[str, Any]) -> Dict[str, Any]:
    """Build the cross-encoder that re-ranks K1 candidates down to K2 chunks.

    Parameters
    ----------
    candidate_retriever : dict[str, Any]
        The single child retriever whose ``top_k`` is the candidate pool size.

    Returns
    -------
    dict[str, Any]
        A ``{"component", "params"}`` retriever reference.
    """
    return {
        "component": RETRIEVER_CROSS_ENCODER,
        "params": {
            "model_name": CROSS_ENCODER_MMARCO_MULTILINGUAL,
            "top_k": PUB5_RERANK_TOP_K,
            "children": [candidate_retriever],
        },
    }


def _query_transformation_llm() -> Dict[str, Any]:
    """Build the Qwen 2.5 7B Instruct LLM used by the transformation stage."""
    return {
        "component": GEN_QWEN_7B,
        "params": {
            "max_tokens": 256,
            "temperature": 0.1,
            "frequency_penalty": 0.0,
            "context_window": 4096,
            "device": "CPU",
        },
    }


def _query_transformation(
    component: str,
    prompt_component: str,
    prompt_templates: Dict[str, str],
    **technique_params: Any,
) -> Dict[str, Any]:
    """Build a publication 5 query-transformation stage reference.

    Parameters
    ----------
    component : str
        Registered transformer class (rewriter, decomposer or expander).
    prompt_component : str
        Registered default prompt class the transformer formats.
    prompt_templates : dict[str, str]
        The prompt module's ``TEMPLATES`` mapping (language -> template).
    **technique_params : Any
        Transformer-specific parameters (``n_queries``, ``max_subqueries``).

    Returns
    -------
    dict[str, Any]
        The ``query_transformation`` value of the session parameters.
    """
    return {
        "component": component,
        "params": {
            "prompt": {
                "component": prompt_component,
                "params": {
                    "language": PROMPT_LANGUAGE,
                    "template": prompt_templates[PROMPT_LANGUAGE],
                },
            },
            "llm_model": _query_transformation_llm(),
            "history_window": HISTORY_WINDOW,
            **technique_params,
        },
    }


def _pub5_parameters(
    candidate_retriever: Dict[str, Any],
    query_transformation: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the parameters shared by the publication 5 pipelines.

    Every row chunks like ``pub4b`` (e5-mistral token windows, 300/60),
    re-ranks a K1-candidate pool with the multilingual mmarco cross-encoder
    down to K2 chunks, transforms the query with Qwen 2.5 7B Instruct and
    generates with Llama 3.2 3B Instruct.

    Parameters
    ----------
    candidate_retriever : dict[str, Any]
        Initial retriever producing the K1 candidates.
    query_transformation : dict[str, Any]
        Query-transformation stage of the row.

    Returns
    -------
    dict[str, Any]
        The ``parameters`` of the session payload.
    """
    return {
        "chunking_model": _token_chunking_model(),
        "retriever_model": _cross_encoder_reranker(candidate_retriever),
        "generation_model": _generation_model(GEN_LLAMA_3B),
        "prompt": _rag_generation_prompt(),
        "query_transformation": query_transformation,
    }


def get_pub5a_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 5a: Query Rewriting — BM25 -> cross-encoder -> Llama 3.2 3B.

    ``LLMQueryRewriter`` rewrites each user message into a single
    self-contained search query (``history_window=2``, default English
    rewriting prompt, Qwen 2.5 7B Instruct). The rewritten query retrieves K1
    candidates from BM25 over a ``BagOfWordsConverter`` vectorizer, which the
    ``cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`` re-ranker narrows to K2.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 5a - Query Rewriting (BM25 + CrossEncoder)",
        "description": None,
        "parameters": _pub5_parameters(
            _bm25_candidate_retriever(),
            _query_transformation(
                "LLMQueryRewriter",
                "DefaultQueryRewritingPrompt",
                REWRITING_PROMPT_TEMPLATES,
            ),
        ),
    }


def get_pub5b_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 5b: Query Decomposition — MiniLM -> cross-encoder -> Llama 3.2 3B.

    ``LLMQueryDecomposer`` splits each user message into at most
    ``max_subqueries=4`` sub-queries (``history_window=2``, default English
    decomposition prompt, Qwen 2.5 7B Instruct). The sub-queries retrieve K1
    candidates each from a ``DenseEmbeddingRetriever`` over
    ``AllMiniLML6V2Embedding``, which the mmarco cross-encoder narrows to K2.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 5b - Query Decomposition (MiniLM + CrossEncoder)",
        "description": None,
        "parameters": _pub5_parameters(
            _minilm_candidate_retriever(),
            _query_transformation(
                "LLMQueryDecomposer",
                "DefaultQueryDecompositionPrompt",
                DECOMPOSITION_PROMPT_TEMPLATES,
                max_subqueries=MAX_SUBQUERIES,
            ),
        ),
    }


def get_pub5c_config(doc_ids: List[int]) -> Dict[str, Any]:
    """Pub 5c: Query Expansion — TF-IDF -> cross-encoder -> Llama 3.2 3B.

    ``LLMQueryExpander`` expands each user message into ``n_queries=3``
    queries (``history_window=2``, default English expansion prompt, Qwen 2.5
    7B Instruct). The queries retrieve K1 candidates each from a
    ``TFIDFRetriever`` over a ``TFIDFConverter`` vectorizer, which the mmarco
    cross-encoder narrows to K2.

    Parameters
    ----------
    doc_ids : list[int]
        IDs of all documents to use as the conversation corpus. Retained for
        signature compatibility; currently ignored.

    Returns
    -------
    dict[str, Any]
        Session payload for the RAG pipeline.
    """
    return {
        "model_name": "RAGPipeline",
        "task_name": "RAGTask",
        "name": "Pub 5c - Query Expansion (TFIDF + CrossEncoder)",
        "description": None,
        "parameters": _pub5_parameters(
            _tfidf_candidate_retriever(),
            _query_transformation(
                "LLMQueryExpander",
                "DefaultQueryExpansionPrompt",
                EXPANSION_PROMPT_TEMPLATES,
                n_queries=N_QUERIES,
            ),
        ),
    }


PIPELINE_REGISTRY = {
    "pub1": {"name": "Publication 1 - Medical Fitness", "config_fn": get_pub1_config},
    "pub2": {"name": "Publication 2 - EHR Summarization", "config_fn": get_pub2_config},
    "pub3": {"name": "Publication 3 - Case Study", "config_fn": get_pub3_config},
    "pub4a": {
        "name": "Publication 4a - RAGChecker Dense",
        "config_fn": get_pub4a_config,
    },
    "pub4b": {
        "name": "Publication 4b - RAGChecker Sparse",
        "config_fn": get_pub4b_config,
    },
    "pub5a": {
        "name": "Publication 5a - Query Rewriting (BM25 + CrossEncoder)",
        "config_fn": get_pub5a_config,
    },
    "pub5b": {
        "name": "Publication 5b - Query Decomposition (MiniLM + CrossEncoder)",
        "config_fn": get_pub5b_config,
    },
    "pub5c": {
        "name": "Publication 5c - Query Expansion (TFIDF + CrossEncoder)",
        "config_fn": get_pub5c_config,
    },
}
