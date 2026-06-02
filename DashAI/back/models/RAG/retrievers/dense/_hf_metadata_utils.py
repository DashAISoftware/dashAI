from typing import Dict, List

from DashAI.back.models.RAG.retrievers.dense._hf_language_utils import (
    build_family_language_summary,
    build_model_language_summaries,
)


def build_retriever_metadata(
    models: Dict[str, dict],
    family_name: str,
    model_count: int,
) -> Dict[str, object]:
    family_summary, family_count = build_family_language_summary(models)
    model_languages = build_model_language_summaries(models)
    return {
        "family": family_name,
        "language_summary": family_summary,
        "language_count": family_count,
        "model_count": model_count,
        "model_languages": model_languages,
    }
