"""Fit a chat history into the model's context window (#977).

When the conversation no longer fits, the oldest turns are folded into a
summary written by the same model. The summary is sent first, as a user
message followed by a short assistant acknowledgement, so chat templates that
require strict user/assistant alternation accept it. Nothing here touches the
database: the job stores the result.
"""

from dataclasses import dataclass
from typing import Callable

SUMMARY_PREFIX = "Summary of the earlier conversation:\n"
SUMMARY_ACK = "Understood."
SUMMARY_INSTRUCTION = (
    "Summarize the conversation below. Write one short paragraph in third "
    "person about the user. Do not copy the dialogue. Keep names, places, "
    "numbers, decisions and preferences. Use the language of the conversation."
)

Prepare = Callable[[list[tuple[str, str]]], list[dict[str, str]]]
Turn = tuple[int, str, str]


class ContextOverflowError(Exception):
    """The current message does not fit the context window, even summarized."""

    def __init__(self, needed: int, window: int):
        self.needed = needed
        self.window = window
        super().__init__(
            f"Conversation too long for the context window ({needed} of "
            f"{window} tokens). Increase context_window or start a new session."
        )


class SummarizationError(Exception):
    """The model could not write the summary of the earlier turns."""


@dataclass
class FittedHistory:
    """The messages to send, and the summary they were built with."""

    messages: list[dict[str, str]]
    summary: str | None
    summary_until: int | None
    changed: bool


def _summary_messages(summary: str) -> list[dict[str, str]]:
    return [
        {"role": "user", "content": SUMMARY_PREFIX + summary},
        {"role": "assistant", "content": SUMMARY_ACK},
    ]


def _build(prepare: Prepare, summary: str | None, recent: list[Turn]):
    head = _summary_messages(summary) if summary else []
    return head + prepare([(i, o) for _, i, o in recent])


def _summary_prompt(summary: str | None, turns: list[Turn]) -> dict[str, str]:
    parts = [SUMMARY_INSTRUCTION]
    if summary:
        parts.append(f"Previous summary:\n{summary}")
    transcript = "\n\n".join(f"User: {i}\nAssistant: {o}" for _, i, o in turns)
    parts.append(f"New turns:\n{transcript}")
    return {"role": "user", "content": "\n\n".join(parts)}


def _summarize(model, prompt: dict[str, str], cap: int) -> str:
    previous = model.max_tokens
    model.max_tokens = cap
    try:
        summary = model.generate([prompt])[0].strip()
    except Exception as e:
        raise SummarizationError(str(e)) from e
    finally:
        model.max_tokens = previous
    # An empty summary would silently drop the folded turns from every
    # later prompt.
    if not summary:
        raise SummarizationError("The model returned an empty summary.")
    return summary


def _prompt_tokens(model, summary: str | None, turns: list[Turn]) -> int:
    return model.count_tokens([_summary_prompt(summary, turns)])


def _next_fold(
    model,
    summary: str | None,
    recent: list[Turn],
    limit: int,
    overflow: ContextOverflowError,
):
    """Choose the oldest turns to fold next, cutting a lone turn if needed.

    Returns the turns to summarize (possibly with their text cut) and how many
    of ``recent`` they stand for. Keeps the most recent turn out of the fold
    when there is more than one turn. Raises ``overflow``, which carries the
    conversation's real need, when not even a cut turn can be summarized.
    """
    max_k = max(1, len(recent) - 1)
    k = 0
    for n in range(1, max_k + 1):
        if _prompt_tokens(model, summary, recent[:n]) > limit:
            break
        k = n
    if k:
        return recent[:k], k

    process_id, user_text, answer = recent[0]
    # With both texts empty the prompt is just the instruction and the
    # previous summary; if that does not fit, cutting cannot help.
    base = _prompt_tokens(model, summary, [(process_id, "", "")])
    if base > limit:
        raise overflow
    while _prompt_tokens(model, summary, [(process_id, user_text, answer)]) > limit:
        user_text = user_text[: len(user_text) // 2]
        answer = answer[: len(answer) // 2]
    return [(process_id, user_text, answer)], 1


def fit_history(
    model,
    prepare: Prepare,
    turns: list[Turn],
    summary: str | None,
    summary_until: int | None,
) -> FittedHistory:
    """Build the messages to send, folding old turns into the summary if needed.

    Parameters
    ----------
    model : BaseGenerativeModel
        The loaded model; it counts tokens and writes the summary.
    prepare : callable
        Turns ``(input, output)`` pairs into the full message list, current
        message included.
    turns : list of (int, str, str)
        ``(process_id, input, output)`` of the finished turns after
        ``summary_until``, oldest first.
    summary : str or None
        The stored summary.
    summary_until : int or None
        Id of the last turn the stored summary covers.

    Returns
    -------
    FittedHistory
        The messages, the summary they use and whether it changed.

    Raises
    ------
    ContextOverflowError
        When the current message does not fit, even with every turn folded.
    SummarizationError
        When the model fails to write the summary.
    """
    messages = _build(prepare, summary, turns)
    limits = model.context_limits()
    if limits is None or model.count_tokens(messages) is None:
        return FittedHistory(messages, summary, summary_until, False)

    window, max_tokens = limits
    # max_tokens has no upper bound and llama.cpp clamps the reply to the
    # space left, so a reserve as large as the window must not leave the
    # prompt without room.
    reserve = min(max_tokens, window // 2)
    budget = window - reserve
    cap = max(32, window // 4)
    # Folding cannot help a current message that does not fit on its own.
    alone = model.count_tokens(prepare([]))
    if alone > budget:
        raise ContextOverflowError(needed=alone + reserve, window=window)
    recent = list(turns)
    changed = False
    while True:
        messages = _build(prepare, summary, recent)
        count = model.count_tokens(messages)
        if count <= budget:
            return FittedHistory(messages, summary, summary_until, changed)
        if not recent:
            raise ContextOverflowError(needed=count + reserve, window=window)
        overflow = ContextOverflowError(needed=count + reserve, window=window)
        fold, k = _next_fold(model, summary, recent, window - cap, overflow)
        summary = _summarize(model, _summary_prompt(summary, fold), cap)
        summary_until = recent[k - 1][0]
        recent = recent[k:]
        changed = True
