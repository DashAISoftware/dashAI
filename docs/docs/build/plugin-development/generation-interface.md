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

## Compatibility

| Plugin | Host | Behavior |
| --- | --- | --- |
| Only `generate` | Old | Works as before. |
| Only `generate` | New | DashAI adapts its first text reply to `ModelResponse`. |
| `generate` and `generate_result` | Old | The host calls `generate` only. |
| `generate` and `generate_result` | New | The host calls `generate_result` once. |

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

    def _call_provider(self, messages):
        # Replace this deterministic response with one provider request.
        return {"answer": "Answer", "reasoning": "Plan"}

    def generate(self, prompt):
        return [self._call_provider(prompt)["answer"]]

    def generate_result(self, messages):
        # Lazy imports let the plugin still import on older hosts.
        from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart

        from DashAI.back.core.generation import to_chat_messages

        response = self._call_provider(to_chat_messages(messages))
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

An enriched method may return a mapping shaped like native `ModelResponse`:
`{"parts": [{"part_kind": "text", "content": "Answer"}]}`. DashAI validates it
with a native Pydantic type adapter. `TextPart` and `ThinkingPart` use `content`,
not DashAI's former `text` field. No aliases for the unreleased custom DTOs remain.

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
   answer or attachment contents in logs or stored error messages.

Validation follows the native Pydantic AI schema, not the removed custom DTOs.
The bridge also rejects negative token counts and negative/nonfinite audio duration.
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
