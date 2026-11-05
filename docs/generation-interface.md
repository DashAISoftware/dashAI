# Text generation interface

Text generation has a provider-independent, opt-in interface alongside the
existing `generate(prompt) -> list[str]` contract. It is the first step toward
[RFC #976](https://github.com/DashAISoftware/dashAI/issues/976).

The public types live in `DashAI.back.core.generation`:

- `GenerationRequest`: a nonempty conversation of `GenerationMessage` objects.
- `GenerationMessage`: a `system`, `user` or `assistant` role with ordered parts.
- `TextPart` and `ReasoningPart`: explicit text and reasoning; neither is inferred
  from the other. These are the only supported part types in this release.
- `GenerationResult`: ordered reply parts, optional `GenerationUsage` and an
  optional provider `finish_reason`. Its `text` property joins only text parts,
  preserving whitespace. Reasoning-only results are valid and have empty text.
- `GenerationUsage`: optional nonnegative token counts and backend-reported load
  and generation durations in seconds. Missing measurements remain `None`.

The types validate their data using the existing Pydantic dependency. Unknown
fields, unsupported part types and invalid measurements fail explicitly. Results
can be serialized using `model_dump_json` and read with `model_validate_json`.

## Model integration

`TextToTextGenerationTaskModel.generate_result(request)` converts the request to
the existing role/content messages, calls `generate` once and normalizes its first
reply. Existing subclasses do not need to implement anything new. Conversion to
the legacy input rejects non-text parts instead of silently discarding them.

A model that can supply richer output overrides `generate_result`. For example:

```python
def generate_result(self, request):
    from DashAI.back.core.generation import GenerationResult, ReasoningPart, TextPart

    response = self._request(request.to_messages())
    return GenerationResult(
        parts=[
            ReasoningPart(text=response.reasoning),
            TextPart(text=response.answer),
        ],
        finish_reason=response.finish_reason,
    )
```

This example assumes a model-specific `_request` that makes one provider call;
provider adapters own the mapping and error handling. They must retain `generate`
for callers using older DashAI installations. Both methods should share the
provider request implementation without invoking both generation paths. An
optional enriched method can import the new types inside that method, so importing
the plugin on an older host does not require those types. It can also return a
mapping conforming to `GenerationResult`, which DashAI validates.

The shared `generate_text(model, messages)` entry point is used by chat and by
the LLM stage of RAG. It also accepts legacy plugins that only expose `generate`,
without inheriting the base class. If an enriched method exists, failures or
invalid results propagate; they never trigger a second call through `generate`.
The legacy first-reply convention is unchanged.

Only text-to-text generation uses this contract. Image, audio, video and RAG's
retrieval/document input retain their existing interfaces. A completion model
requiring a raw string needs its own explicit input adapter; this layer does not
guess chat templates or flatten arbitrary messages into a completion prompt.

## Storage and session compatibility

This change keeps the existing schema parameters, credential lookup and session
configuration. No user setting selects an interface version. New DashAI adapts
old text plugins; a new plugin retains its legacy method for old DashAI.

The chat task still stores only the final answer as a `ProcessData` of type `str`.
RAG keeps its existing `message` and `chunks` fields and adds an optional
`generation_result` for downstream consumers. The current RAG task stores the
same answer and chunk references as before.

Reasoning and usage are available in memory but are not persisted or exposed by
the process API in this change. Structured storage and the chat reasoning panel
belong to the following PR; they must consume this result rather than inventing
another provider-specific output shape. Existing history and rows are unchanged.

## Compatibility and extension policy

The presence of `generate_result` is the opt-in contract. Package version
comparisons, imports of private host modules and an interface-version setting
are unnecessary. Both methods coexist; removing the legacy method would be a
separately announced incompatible change.

Adding an optional field lets existing producers keep working with a new consumer.
An older consumer rejects unknown fields, so producers must not start sending new
fields until their consumer supports them. New required fields, renamed fields,
changed meanings or new parts require an explicit migration. A serialized storage
format should carry a schema
version when it is introduced; no storage format is introduced here.

Tools, multimodal parts, streaming, cancellation, automatic retries and choosing
an agent framework remain separate work. No agent-framework dependency is added.
The legacy `generate` method remains abstract: this interface does not implicitly
make a model usable on an older host without its legacy implementation.
