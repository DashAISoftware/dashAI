---
title: Generation Interface
sidebar_label: Generation Interface
---

# Generation interface

Text-generation plugins should implement **`generate_result`**, which receives and
returns the native message types of [Pydantic AI](https://ai.pydantic.dev/api/messages/).
This is the current interface. It lets a model return its reasoning and measured
token usage next to the answer, and it can carry images, audio, video and documents
(see [issue #976](https://github.com/DashAISoftware/dashAI/issues/976)).

:::warning Migrate legacy plugins
The older way of writing a text model, `generate(messages)` returning `List[str]`,
and the `GenerationRequest` / `GenerationResult` classes from an earlier draft are
**legacy**. They still work today, but new plugins must not use them and existing
plugins should migrate. See [Migrating an existing plugin](#migrating-an-existing-plugin).
:::

DashAI depends on `pydantic-ai-slim>=2.66,<3`, without provider SDKs. There is no
second DashAI message schema: import everything from Pydantic AI.

| You need | Import |
| --- | --- |
| Conversation and reply types | `ModelMessage`, `ModelRequest`, `ModelResponse` from `pydantic_ai.messages` |
| Reply content | `TextPart`, `ThinkingPart` from `pydantic_ai.messages` |
| Input content | `UserPromptPart`, `SystemPromptPart`, and for attachments `ImageUrl`, `AudioUrl`, `VideoUrl`, `DocumentUrl`, `BinaryContent` |
| Token usage | `RequestUsage` from `pydantic_ai.usage` |

## Write a plugin

Extend `TextToTextGenerationTaskModel` and override `generate_result`. Model
parameters, credentials and the `__init__` schema work exactly as before. You do
not need to implement `generate`: the base class provides one that returns the
answer text of your `generate_result`.

```python
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ThinkingPart,
    UserPromptPart,
)
from pydantic_ai.usage import RequestUsage

from DashAI.back.models.text_to_text_generation_model import (
    TextToTextGenerationTaskModel,
)


class MyModel(TextToTextGenerationTaskModel):
    def __init__(self, **kwargs):
        pass  # Your existing schema and model setup.

    def generate_result(self, messages):
        # `messages` is a list[ModelMessage] in conversation order.
        question = next(
            part.content
            for message in reversed(messages)
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, UserPromptPart)
        )
        reply = self._call_provider(question)  # One provider request.
        return ModelResponse(
            parts=[
                ThinkingPart(content=reply["reasoning"]),  # Optional.
                TextPart(content=reply["answer"]),
            ],
            usage=RequestUsage(input_tokens=12, output_tokens=7),  # Optional.
        )

    def _call_provider(self, question):
        # Replace this deterministic response with a real provider request.
        return {"answer": "Answer", "reasoning": "Plan"}
```

### Reading the input

`messages` mixes two native types, in order:

- `ModelRequest`: system and user turns. Its `parts` hold `SystemPromptPart` and
  `UserPromptPart`; a user part's `content` is a `str`, or a list that mixes text
  with `ImageUrl`, `AudioUrl`, `VideoUrl`, `DocumentUrl` and `BinaryContent`.
- `ModelResponse`: earlier assistant turns, made of `TextPart` and `ThinkingPart`.

### Building the output

| You want to return | Put in the `ModelResponse` |
| --- | --- |
| The answer | One or more `TextPart(content=...)` |
| The model's reasoning | A `ThinkingPart(content=...)` before the text |
| Measured usage | `usage=RequestUsage(input_tokens=..., output_tokens=...)` |
| Why generation stopped | `finish_reason="stop"` (or `"length"`, `"content_filter"`) |

Only report usage the provider measured. A `RequestUsage()` with default zeros is
indistinguishable from "zero tokens", and DashAI does not show it as a measurement.

You may also return a mapping shaped like a `ModelResponse`, for example
`{"parts": [{"part_kind": "text", "content": "Answer"}]}`. DashAI validates it
with Pydantic AI's own schema and ignores unknown extra keys.

### Supporting older DashAI versions too

Hosts that predate this interface never call `generate_result`; they only call
`generate`. If your plugin must still run there, keep a `generate` method that
returns `List[str]` and import `pydantic_ai` lazily inside `generate_result`, so
that the plugin module imports on those hosts. If you only target the current
DashAI, implement `generate_result` alone and import `pydantic_ai` at the top of the
module as in the example above.

## Migrating an existing plugin

### From `generate` to `generate_result`

| Before (legacy) | After |
| --- | --- |
| `def generate(self, messages)` with `[{"role": "user", "content": "..."}]` | `def generate_result(self, messages)` with native `ModelMessage` objects |
| `return ["answer"]` | `return ModelResponse(parts=[TextPart(content="answer")])` |
| Reasoning mixed into the answer text, or lost | `ThinkingPart(content=...)` |
| Token counts unavailable | `usage=RequestUsage(...)` |

Plugins that only implement `generate` keep working, but they cannot return
reasoning or usage. DashAI adapts their first reply to a `ModelResponse` with
default (not measured) usage.

### From the earlier draft classes

An earlier iteration of this interface defined `GenerationRequest`,
`GenerationMessage`, `GenerationResult`, `GenerationUsage`, `TextPart` (field
`text`) and `ReasoningPart` in `DashAI.back.core.generation`. They are **deprecated
and will be removed in a future major release.** Today the names still import from
that module with a `DeprecationWarning`, and plugins written against them keep
working: a returned `GenerationResult` is converted to a `ModelResponse`, and the
`messages` argument still answers `to_messages()` and `.messages`.

| Draft class | Replace with |
| --- | --- |
| `GenerationRequest` argument and `request.to_messages()` | The `list[ModelMessage]` argument itself |
| `GenerationResult(parts=[...])` | `ModelResponse(parts=[...])` |
| `TextPart(text=...)` | `TextPart(content=...)` from `pydantic_ai.messages` |
| `ReasoningPart(text=...)` | `ThinkingPart(content=...)` from `pydantic_ai.messages` |
| `GenerationUsage(prompt_tokens=..., completion_tokens=...)` | `RequestUsage(input_tokens=..., output_tokens=...)` |
| `GenerationUsage(generation_seconds=..., load_seconds=...)` | `ModelResponse(provider_details={...})` |
| `finish_reason="stop"` | `ModelResponse(finish_reason="stop")` |

## How DashAI calls your model

The built-in chat task and the LLM stage of RAG go through
`DashAI.back.core.generation.generate_text(model, messages)`:

| Plugin | Behavior |
| --- | --- |
| Has `generate_result` | Called once with native messages. |
| Only `generate` | Called once with role/content dictionaries; its first reply is wrapped. |
| A raw Pydantic AI `Model` | Called with `model_request_sync`; no `Agent`, tools or DashAI retry. |

A single generation never calls both methods. If the reply is invalid or the
provider fails, the error is raised; DashAI does **not** retry through `generate`.
Provider SDKs may have their own retry policy.

### Validation and errors

1. The conversation is validated before generation. Native messages are checked
   against Pydantic AI's schema on a snapshot, because its dataclasses are mutable.
2. Your reply is validated the same way. Negative token counts and negative or
   non-finite audio durations are rejected.
3. Validation errors name the field and the reason but never repeat prompt, answer
   or attachment contents. This covers errors from the bridge only: an exception
   raised by your provider code is logged and stored as before, so do not put
   prompt text in your own exception messages.

For legacy `generate` plugins two checks are stricter than before the bridge
existed: each history item must have exactly `role` and a string `content` (an
extra key such as `name` is rejected), and `generate` must return a list or tuple
whose first item is a string.

### Threading

`generate_text` is synchronous and blocks until the provider answers. It is built
for the generative job, which runs in a worker thread. A raw Pydantic AI `Model`
goes through `model_request_sync`, which raises
`RuntimeError: This event loop is already running` inside a running event loop. Do
not call `generate_text` from an `async` endpoint handler; run it in a thread.

### Custom tasks

Custom task plugins, including subclasses of the built-in text task, keep calling
`model.generate` with their own input and output. The job does not assume their
`prepare_for_task` or `process_output` understand native messages.

## Attachments and multimodal input

A `UserPromptPart` may contain `ImageUrl`, `AudioUrl`, `VideoUrl`, `DocumentUrl` and
`BinaryContent`. DashAI hands them unchanged to a model that implements
`generate_result`. A legacy `generate` model rejects them with an error before any
provider call. The bridge does not download referenced files.

This does not turn on attachments in the chat UI or guarantee that a given provider
accepts a modality. Upload handling, per-model capability checks, size limits and
persistence are separate steps in the [migration plan](./pydantic-ai-migration.md).

## What is stored today

The chat task stores only the answer as a `str`. RAG keeps its `message` and
`chunks` and carries the full `ModelResponse` in memory as `generation_result`.

The answer is the concatenation of the `TextPart` contents, with whitespace kept
and `ThinkingPart` excluded. Until structured storage exists, a reply that has
only reasoning, or that contains tool or multimodal output, fails with an explicit
error instead of being silently dropped. An explicit empty `TextPart` still gives
an empty answer. Reasoning and usage are not yet shown or exposed by the API.

## Testing your plugin

- Use Pydantic AI's `FunctionModel` to test code that consumes a `ModelResponse`
  without credentials or network.
- A bare `MagicMock` pretends to have `generate_result`. For a legacy plugin use
  `Mock(spec=["generate"])`.
- To save or replay a conversation, use
  `ModelMessagesTypeAdapter.dump_json(messages)` and `.validate_json(data)`.
  Native messages are mutable, so do not share and modify one history.
