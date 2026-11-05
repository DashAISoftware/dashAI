---
title: Text Generation Interface
sidebar_label: Text Generation Interface
---

# Text generation interface

Text models have always returned a plain `list[str]` from `generate(prompt)`. That
cannot carry reasoning, token usage or a finish reason. DashAI now defines a
provider-independent, **opt-in** interface next to the existing contract. It is
related to [issue #976](https://github.com/DashAISoftware/dashAI/issues/976)
(option B: DashAI-owned types).

You only need this page if you want your plugin to return richer output. **Existing
plugins keep working without any change.**

## At a glance

| Your plugin                      | DashAI host | What happens                                                    |
| -------------------------------- | ----------- | --------------------------------------------------------------- |
| Only `generate`                  | old         | Works as before.                                                |
| Only `generate`                  | new         | DashAI adapts it: the first reply becomes the answer.           |
| `generate` + `generate_result`   | old         | Works: the old host only calls `generate`.                      |
| `generate` + `generate_result`   | new         | DashAI calls `generate_result` **once** and never `generate`.   |

The presence of `generate_result` is the opt-in. Do not compare DashAI versions and
do not import private host modules; there is no interface-version setting.

## The types

They live in `DashAI.back.core.generation` and are validated with Pydantic
(strict types, unknown fields rejected, instances immutable once created).

- `TextPart` and `ReasoningPart`: answer text and reasoning, as separate parts. One
  is never inferred from the other. These are the only part types in this release.
- `GenerationMessage`: a `system`, `user` or `assistant` role with at least one part.
- `GenerationRequest`: at least one message.
- `GenerationUsage`: optional non-negative token counts and backend-reported
  `generation_seconds` / `load_seconds`. Missing values stay `None`. DashAI does not
  check that `total_tokens` equals prompt plus completion tokens.
- `GenerationResult`: at least one part, optional `usage` and optional
  `finish_reason`. Its `text` property joins only the text parts in order and keeps
  whitespace; reasoning is never mixed into it.

Results can be serialized with `model_dump_json()` and read back with
`model_validate_json()`.

## Making a plugin return richer output

Keep `generate` for old hosts and add `generate_result` for new ones. Both should
share one provider call implementation, and each must call the provider **once**.

```python
from typing import List

from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)


class MyModel(TextToTextGenerationTaskModel):
    def __init__(self, **kwargs):
        ...  # your usual model setup

    def _call_provider(self, messages: list[dict[str, str]]):
        """Your single provider call. Returns an object with .answer,
        .reasoning (or None) and .finish_reason."""
        ...

    def generate(self, prompt: list[dict[str, str]]) -> List[str]:
        # Legacy path, still used by older DashAI versions.
        return [self._call_provider(prompt).answer]

    def generate_result(self, request):
        # Imported here so the plugin still imports on a host that does not
        # have these types yet.
        from DashAI.back.core.generation import (
            GenerationResult,
            ReasoningPart,
            TextPart,
        )

        response = self._call_provider(request.to_messages())
        parts = [TextPart(text=response.answer)]
        if response.reasoning:
            parts.insert(0, ReasoningPart(text=response.reasoning))
        return GenerationResult(parts=parts, finish_reason=response.finish_reason)
```

`generate_result` may also return a plain mapping shaped like `GenerationResult`;
DashAI validates it. `request.to_messages()` gives the same
`[{"role": ..., "content": ...}]` list that `generate` receives, and raises
`ValueError` if the request has non-text parts instead of silently dropping them.

If you do not override `generate_result`, the base class implementation calls your
`generate` once and wraps its first reply.

## What DashAI checks

Chat and the LLM stage of RAG both go through `generate_text(model, messages)`:

1. The messages must be dictionaries with exactly the keys `role` and `content`,
   where `role` is `system`, `user` or `assistant` and `content` is a string.
   Anything else raises `ValueError` **before** the provider is called.
2. If `model.generate_result` is callable, it is called once and its result is
   validated. If it raises or returns invalid data, that error is reported; DashAI
   never falls back to `generate`, so the provider is never called twice.
3. Otherwise `model.generate` is called once. A duck-typed plugin that only has
   `generate` and does not inherit the base class is accepted.

Errors name the invalid field and the reason, never the prompt or answer text.

### Legacy output is validated

`generate` must return a `list` or `tuple` whose first item is a `str`. Only the
first item is used; further replies are ignored. Output such as `None`, `[None]` or
`[42]` now fails the generation with a clear error. Before this interface, chat
stored it as the text `"None"` or `"42"`; RAG already rejected it. Return strings
from `generate`.

### Tests that use mocks

Because `generate_result` is looked up by attribute, a bare `MagicMock()` appears to
have it and returns another mock, which fails validation. Use
`MagicMock(spec=["generate"])` for a legacy plugin.

## Scope, storage and sessions

Only text-to-text generation uses this contract. Image, audio and video models, and
RAG's retrieval and document input, keep their interfaces. A completion model that
needs a raw string must provide its own input adapter; DashAI does not guess chat
templates.

Session parameters, credential lookup and the stored history are unchanged. The chat
task still stores only the final answer as a `str` `ProcessData`. RAG keeps its
`message` and `chunks` and adds an optional in-memory `generation_result`.

Reasoning and usage are **not persisted or exposed by the API yet**. They will be in
a following change that consumes this same result type. Until then:

- A reply that contains reasoning but **no text part** is an error in chat
  ("The model returned reasoning but no answer text"), because there would be
  nothing to store. Always include a `TextPart` with the answer.
- A reply whose text part is the empty string is stored as an empty answer, as
  before.

## Compatibility policy

Adding an optional field lets existing producers work with a newer consumer. An
older consumer rejects unknown fields, so do not send new fields before the consumer
supports them. New required fields, renamed fields, changed meanings or new part
types need an explicit migration, and any stored format must carry a schema version
when one is introduced. None is introduced here.

The legacy `generate` method stays abstract and supported; removing it would be a
separately announced breaking change. Tools, multimodal parts, streaming,
cancellation, automatic retries and the choice of an agent framework
([#974](https://github.com/DashAISoftware/dashAI/issues/974)) are separate work, and
no agent-framework dependency is added.
