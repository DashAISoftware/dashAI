---
title: Generation Interface
sidebar_label: Generation Interface
---

# Generation interface

DashAI uses the native message and response types of **Pydantic AI** for enriched
text-generation calls, following [issue #976](https://github.com/DashAISoftware/dashAI/issues/976).
The dependency is `pydantic-ai-slim>=2.66,<3`; provider SDK extras are not installed
in the host just to define the contract. `uv.lock` fixes the tested version.

There is no second DashAI message schema. Import `ModelMessage`, `ModelRequest`,
`ModelResponse`, `TextPart`, `ThinkingPart`, and the multimodal content types from
`pydantic_ai.messages`; token usage is `pydantic_ai.usage.RequestUsage`.

Existing plugins keep working without any change. Model parameters and credentials
remain in the existing DashAI schemas and credential store.

## What your plugin should return

| You want to return | Implement | Return |
| --- | --- | --- |
| Only the answer text | `generate` | `["answer"]` (a list or tuple; the first item is used) |
| Answer and reasoning | `generate_result` | `ModelResponse(parts=[ThinkingPart(...), TextPart(...)])` |
| Measured token usage | `generate_result` | The same `ModelResponse` with `usage=RequestUsage(input_tokens=..., output_tokens=...)` |

Always keep `generate` too, so the plugin still runs on older DashAI versions.

## Compatibility

| Plugin | Host | Behavior |
| --- | --- | --- |
| Only `generate` | Old | Works as before. |
| Only `generate` | New | DashAI adapts its first text reply to `ModelResponse`. |
| `generate` and `generate_result` | Old | The host calls `generate` only. |
| `generate` and `generate_result` | New | The host calls `generate_result` once. |

Roles, content and message order are preserved. Two behaviors differ from before
the bridge existed, so check your plugin and tests:

- Chat history passed to the bridge must contain dictionaries with exactly `role`
  and a string `content`. A dictionary with an extra key (for example `name`) is
  rejected before generation instead of being forwarded to the plugin.
- Legacy `generate` output must be a list or tuple whose first item is a string.
  A dictionary or other object as the first item is rejected.

The public bridge is `DashAI.back.core.generation`. `from_chat_messages` converts
existing role/content dictionaries to native messages; `to_chat_messages` performs
the inverse for text-only legacy models. Both preserve conversation order and
whitespace. An assistant response with adjacent text parts becomes one assistant
message. Unsupported parts are rejected rather than silently removed.

`TextToTextGenerationTaskModel.generate_result(messages)` has a default
implementation that calls the existing `generate` method once. Duck-typed plugins
with only `generate` are also accepted. Legacy output may be a list or tuple, and
its first element must be a string; further replies are ignored, as before.

A raw Pydantic AI `Model` instance is also accepted by the common `generate_text`
helper. It is called through `model_request_sync` without an `Agent`, tool loop or
DashAI retry/fallback. Provider SDKs may have their own retry policy. A Pydantic AI
model still needs a DashAI component wrapper to supply registry metadata, schema
parameters and credentials when offered in the UI.

:::warning Synchronous call
`generate_text` blocks until the provider replies, and `model_request_sync` raises
`RuntimeError: This event loop is already running` inside a running event loop.
It is designed for the generative job, which runs in a worker thread. Do not call
it from an `async` endpoint handler; run it in a thread instead.
:::

## Enriched plugins

Keep `generate` for older hosts and implement `generate_result` using native
Pydantic AI messages. Both methods should share the provider request implementation;
a single generation must never call both methods.

```python
from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)


class MyModel(TextToTextGenerationTaskModel):
    def __init__(self, **kwargs):
        pass  # Your existing schema and model setup.

    def _call_provider(self, question):
        # Replace this deterministic response with one provider request.
        return {"answer": "Answer", "reasoning": "Plan"}

    def generate(self, prompt):
        # Older hosts and legacy tasks pass [{"role": ..., "content": ...}].
        return [self._call_provider(prompt[-1]["content"])["answer"]]

    def generate_result(self, messages):
        # Lazy imports let the plugin still import on older hosts.
        from pydantic_ai.messages import (
            ModelRequest,
            ModelResponse,
            TextPart,
            ThinkingPart,
            UserPromptPart,
        )

        # Read the native messages directly; no conversion helper is needed.
        question = next(
            part.content
            for message in reversed(messages)
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        response = self._call_provider(question)
        return ModelResponse(
            parts=[
                ThinkingPart(content=response["reasoning"]),
                TextPart(content=response["answer"]),
            ]
        )
```

If the provider is already supported by Pydantic AI, the enriched method can use
`model_request_sync` with its provider adapter instead of mapping a raw response.
The legacy method must stay independent of new host imports to remain usable on
an older host. Install provider-specific extras in the plugin that uses them.

An enriched method may also return a mapping shaped like native `ModelResponse`:
`{"parts": [{"part_kind": "text", "content": "Answer"}]}`. DashAI validates it
with a native Pydantic type adapter. Unknown extra keys in that mapping are ignored.

## Deprecated types from the earlier draft

An earlier iteration of this interface exposed `GenerationRequest`,
`GenerationMessage`, `GenerationResult`, `GenerationUsage`, `TextPart` (field
`text`) and `ReasoningPart` in `DashAI.back.core.generation`. Plugins written
against it keep working: the names still import from that module with a
`DeprecationWarning`, `generate_result` may still return `GenerationResult`, and
the `messages` argument still answers `to_messages()` and `.messages`.
The host converts the result to a native `ModelResponse` (reasoning becomes
`ThinkingPart`, token counts become `RequestUsage`; durations and finish reasons
that Pydantic AI does not define are kept in `provider_details`).

Do not use these names in new code; they live in
`DashAI.back.core.generation_legacy` and may be removed in a future major release.
Migrate by importing `ModelResponse`, `TextPart`, `ThinkingPart` and `RequestUsage`
from Pydantic AI (`TextPart` and `ThinkingPart` use `content`, not `text`).

## Validation and errors

The built-in text chat task and the LLM stage of RAG use
`generate_text(model, messages)`:

1. Existing messages must have exactly `role` and string `content`, with a
   `system`, `user` or `assistant` role. Invalid inputs fail before generation.
2. Native messages are validated using `ModelMessagesTypeAdapter`. Native
   dataclasses are mutable, so the bridge validates a snapshot instead of trusting
   an already-constructed instance. It also returns a validated response snapshot.
3. An enriched method or native model is called once. Errors and invalid responses
   propagate without retrying through the legacy method.
4. Validation errors report their location and reason without repeating prompt,
   answer or attachment contents. This covers errors raised by the bridge only: an
   exception raised by the provider is still logged and stored as before, so a
   plugin should not put prompt text in its own exception messages.

Validation follows the native Pydantic AI schema. The bridge also rejects negative token counts and negative/nonfinite audio duration.
Native messages are not frozen. Consumers should not mutate shared histories.
Round-trip native history with `ModelMessagesTypeAdapter.dump_json(messages)` and
`ModelMessagesTypeAdapter.validate_json(data)`.

Custom task plugins, including subclasses of the built-in text task, retain the
existing `model.generate` input/output path. The job does not assume their
`prepare_for_task` or `process_output` hooks understand native messages.

A bare `MagicMock` fabricates an enriched method; tests for legacy plugins should
use `Mock(spec=["generate"])`.

## Multimodal boundaries

The native contract represents images, audio, video and documents using
`ImageUrl`, `AudioUrl`, `VideoUrl`, `DocumentUrl` and `BinaryContent` in a
`UserPromptPart`. The bridge preserves those values for capable enriched models.
Converting them to a legacy text-only model raises an error before a provider call.
The bridge itself does not download referenced files.

This does not enable attachments in the existing chat UI or guarantee that a
selected provider accepts a given modality. Upload handling, provider capability
checks, file-size/type limits and structured persistence are separate migration
steps. RAG still owns its loading, chunking, embeddings and retrieval pipeline.
Image generation, ControlNet and other non-chat tasks retain their current paths.

## Storage and measurements

The current chat task stores only the answer as a `str` `ProcessData`. RAG retains
its `message` and `chunks` and carries a native `ModelResponse` in the optional
in-memory `generation_result` field.

`text_answer` joins only `TextPart.content`, keeping whitespace and never including
`ThinkingPart`. Until structured storage exists, tool and multimodal output are
rejected instead of being discarded. Reasoning-only output is also an error;
an explicit empty text part retains the legacy empty-answer behavior.

Provider-reported tokens use `RequestUsage.input_tokens` and `output_tokens`;
`total_tokens` is the library's computed value. Default zero counters in adapted
legacy replies are not measured usage. Do not show them as observed statistics.
Load time and generation duration remain DashAI/provider measurements; no separate
DashAI usage DTO is introduced.

Reasoning and usage are not persisted or exposed by the process API in this PR.
The separate reasoning/chat PR must consume native parts and version any new
stored envelope while continuing to read existing rows. See the
[migration plan](./pydantic-ai-migration.md).
