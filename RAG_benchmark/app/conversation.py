"""Conversation simulation using DeepSeek as a user proxy."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional

from RAG_benchmark.app.config import BenchmarkConfig

log = logging.getLogger(__name__)

_DEFAULT_SYSTEM_PROMPT = (
    "You are simulating a curious user who is studying a technical document "
    "about Retrieval-Augmented Generation (RAG). Your role is to ask natural, "
    "detailed questions about the document content.\n"
    "\n"
    "Guidelines:\n"
    "1. Ask ONE question at a time (short to medium length).\n"
    "2. Vary your questions: ask about definitions, comparisons, specific "
    "details, examples, pros/cons.\n"
    "3. Build on previous answers — show you're following the conversation.\n"
    "4. Never reference that you are an AI or that this is a simulation.\n"
    "5. Sound like a real student or researcher learning about RAG.\n"
    "6. Ask about 1-3 sentences per question.\n"
    "7. If the assistant's answer was unclear, ask a follow-up.\n"
    "8. Avoid asking about things outside the document's scope.\n"
    "9. After several turns, start asking more advanced or synthesis "
    "questions.\n"
    "\n"
    "Current document topic: Retrieval-Augmented Generation (RAG) — "
    "architecture, chunking strategies, retrieval methods (sparse/dense), "
    "ranking, prompt engineering, and challenges."
)


class UserSimulator:
    """Simulates a user asking questions in a multi-turn conversation.

    Uses DeepSeek's chat API to generate contextually relevant follow-up
    questions based on the conversation history.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com",
        system_prompt: Optional[str] = None,
    ) -> None:
        # ``openai`` is an optional dependency: the client is created lazily so
        # that constructing a fallback simulator (empty ``api_key``) and asking
        # fallback questions works even when the package is not installed.
        self._api_key = api_key
        self._base_url = base_url
        self._client: Any = None
        self._model = model
        self._system_prompt = system_prompt or _DEFAULT_SYSTEM_PROMPT
        self._history: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt}
        ]

    @classmethod
    def from_config(cls, config: BenchmarkConfig) -> "UserSimulator":
        if not config.deepseek_api_key:
            raise ValueError(
                "DeepSeek API key is required for conversation simulation. "
                "Set the DASHAI_DEEPSEEK_API_KEY environment variable."
            )
        return cls(
            api_key=config.deepseek_api_key,
            model=config.deepseek_model,
            base_url=config.deepseek_base_url,
        )

    @property
    def history(self) -> List[Dict[str, str]]:
        return list(self._history)

    def reset(self) -> None:
        self._history = [{"role": "system", "content": self._system_prompt}]

    def _get_client(self) -> Any:
        """Return the lazily created OpenAI client.

        Raises
        ------
        RuntimeError
            If the optional ``openai`` package is not installed and a real
            API call (non-empty API key) is attempted.
        """
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as e:
                raise RuntimeError(
                    "The 'openai' package is required to generate questions "
                    "with the DeepSeek API. Install it, or run without an API "
                    "key to use the fallback question pool."
                ) from e
            self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def generate_question(self, assistant_response: Optional[str] = None) -> str:
        if assistant_response is not None:
            self._history.append({"role": "assistant", "content": assistant_response})

        self._history.append(
            {"role": "user", "content": "Continue with your next question."}
        )

        if self._api_key:
            question = self._generate_via_api()
        else:
            question = self._fallback_question()

        self._history.pop()
        self._history.append({"role": "user", "content": question})
        return question

    def _generate_via_api(self) -> str:
        """Ask DeepSeek for the next question, falling back on API errors.

        Missing-package ``RuntimeError`` from :meth:`_get_client` is *not*
        caught here: the caller must learn that a required dependency is
        absent. Transient API errors still fall back to the local pool.
        """
        client = self._get_client()
        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=self._history,
                temperature=0.8,
                max_tokens=256,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            log.warning("DeepSeek question generation failed: %s", e)
            return self._fallback_question()

    def _fallback_question(self) -> str:
        fallbacks = [
            "Can you explain more about how chunking affects retrieval quality?",
            "What are the main differences between sparse and dense retrieval?",
            "How does MMR re-ranking work?",
            "What challenges does RAG face with context window limits?",
            "Can you compare BM25 with embedding-based retrieval?",
            "How do different chunk sizes impact the quality of generated answers?",
            "What role does prompt engineering play in RAG systems?",
            "How does recursive character chunking differ from fixed-size chunking?",
        ]
        return random.choice(fallbacks)
