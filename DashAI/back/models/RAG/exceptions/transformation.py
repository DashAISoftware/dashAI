"""Query transformation RAG exceptions.

The transformation stage is optional, so its failures must be distinguishable
from the rest of the pipeline while still being catchable by the existing
``RAGPipelineRuntimeError`` handlers. ``RAGQueryTransformationError`` is that
stage-level umbrella; the component-level errors below refine it.
"""

from DashAI.back.models.RAG.exceptions.pipeline import RAGPipelineRuntimeError


class RAGQueryTransformationError(RAGPipelineRuntimeError):
    """Typed failure of the optional query transformation stage.

    Raised by ``RAGPipeline`` when the configured transformer fails or returns
    no usable queries. It is a ``RAGPipelineRuntimeError`` so existing callers
    keep catching it, and its ``__cause__`` chain points at the component-level
    failure that ended the stage.
    """


class RAGTransformationError(RAGQueryTransformationError):
    """Base exception for the optional query transformation stage."""


class RAGTransformationConfigError(RAGTransformationError):
    """Invalid configuration for a query transformer.

    Raised when building a transformer with a bad schema (for example an LLM
    of the wrong type) or when a required parameter such as the prompt or the
    LLM model is missing.
    """


class RAGTransformationOutputError(RAGTransformationError):
    """The model output could not be parsed into the function-call contract.

    The message carries a short, truncated preview of the raw output so the
    failure can be diagnosed without leaking full user text.
    """


class RAGTransformationGenerationError(RAGTransformationError):
    """The transformation backend failed while producing the model call.

    Distinct from :class:`RAGTransformationOutputError`: the model was reached
    but the function-calling backend raised (missing call, runtime failure,
    drifted response shape), so the cause chain carries the backend error.
    """
