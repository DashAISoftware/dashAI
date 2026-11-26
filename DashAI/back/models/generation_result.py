"""Typed result of a generative model call.

Implements issue #976. Streaming (``GenerationChunk`` is declared but not yet
used) and typed input (``ChatMessage`` is declared but not yet enforced) are
future work.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union

METADATA_VERSION = 1


@dataclass(frozen=True)
class TextPart:
    """Plain text produced by the model."""

    text: str


@dataclass(frozen=True)
class ReasoningPart:
    """Reasoning text produced by the model before its answer."""

    text: str


@dataclass(frozen=True)
class ToolCallPart:
    """A tool call requested by the model."""

    id: str
    name: str
    arguments: str


Part = Union[TextPart, ReasoningPart, ToolCallPart]


@dataclass(frozen=True)
class Usage:
    """Token accounting for one generation."""

    prompt_tokens: int
    completion_tokens: int

    @property
    def total_tokens(self) -> int:
        """Return prompt plus completion tokens."""
        return self.prompt_tokens + self.completion_tokens


@dataclass(frozen=True)
class GenerationResult:
    """Result of a generation call.

    Parameters
    ----------
    parts : tuple of Part
        Ordered output parts.
    usage : Usage, optional
        Token usage, when reported by the model.
    finish_reason : str, optional
        Why generation stopped, when reported by the model.
    raw_outputs : list, optional
        Original output list, returned as is by ``to_outputs``.
    """

    parts: Tuple[Part, ...] = ()
    usage: Optional[Usage] = None
    finish_reason: Optional[str] = None
    raw_outputs: Optional[List[Any]] = None

    @property
    def text(self) -> str:
        """Concatenation of all text parts, in order."""
        return "".join(p.text for p in self.parts if isinstance(p, TextPart))

    def to_outputs(self) -> List[Any]:
        """Return the legacy list of outputs."""
        if self.raw_outputs is not None:
            return self.raw_outputs
        return [self.text]

    def metadata(self) -> Optional[Dict[str, Any]]:
        """Return JSON-serializable metadata, or None when there is none."""
        meta: Dict[str, Any] = {"version": METADATA_VERSION}
        if self.usage is not None:
            meta["usage"] = {
                "prompt_tokens": self.usage.prompt_tokens,
                "completion_tokens": self.usage.completion_tokens,
            }
        if self.finish_reason is not None:
            meta["finish_reason"] = self.finish_reason
        extra = []
        for part in self.parts:
            if isinstance(part, ReasoningPart):
                extra.append({"type": "reasoning", "text": part.text})
            elif isinstance(part, ToolCallPart):
                extra.append(
                    {
                        "type": "tool_call",
                        "id": part.id,
                        "name": part.name,
                        "arguments": part.arguments,
                    }
                )
        if extra:
            meta["parts"] = extra
        return meta if len(meta) > 1 else None

    @classmethod
    def from_outputs(cls, outputs: List[Any]) -> "GenerationResult":
        """Wrap a legacy output list, keeping it as ``raw_outputs``."""
        parts = tuple(TextPart(o) for o in outputs if isinstance(o, str))
        return cls(parts=parts, raw_outputs=outputs)


def result_from_chat_completion(response: Dict[str, Any]) -> GenerationResult:
    """Build a result from an OpenAI-style chat completion dict.

    Parameters
    ----------
    response : dict
        Chat completion as returned by ``create_chat_completion``.

    Returns
    -------
    GenerationResult
        Text part (absent when the content is None or missing), usage when
        both token counts are reported (None if usage or either count is
        missing), and the finish reason of the first choice.
    """
    choice = response["choices"][0]
    content = (choice.get("message") or {}).get("content")
    parts = (TextPart(content),) if content is not None else ()
    raw_usage = response.get("usage") or {}
    prompt_tokens = raw_usage.get("prompt_tokens")
    completion_tokens = raw_usage.get("completion_tokens")
    usage = None
    if prompt_tokens is not None and completion_tokens is not None:
        usage = Usage(prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)
    return GenerationResult(
        parts=parts, usage=usage, finish_reason=choice.get("finish_reason")
    )


@dataclass(frozen=True)
class GenerationChunk:
    """Incremental piece of a streamed generation (not used yet)."""

    delta: Part
    usage: Optional[Usage] = None
    finish_reason: Optional[str] = None


class ChatMessage(TypedDict):
    """A chat message with a role and text content."""

    role: str
    content: str
