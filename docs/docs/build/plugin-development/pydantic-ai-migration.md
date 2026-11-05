---
title: Pydantic AI Migration
sidebar_label: Pydantic AI Migration
---

# Migration to Pydantic AI

Use Pydantic AI's native model messages and responses as the generative contract,
as proposed in [#976](https://github.com/DashAISoftware/dashAI/issues/976).
Keep DashAI's components, schemas, credential store, tasks and process lifecycle.
The framework's `Model`/direct API can be used without adopting an agent loop.

This plan replaces the custom `GenerationRequest`, `GenerationResult`,
`ReasoningPart` and `GenerationUsage` types from the earlier draft of this PR.
Those types have not been released, so they are removed rather than maintained as
a competing interface. The legacy `generate` contract remains supported.

## 1. Foundation: this PR

- Depend on `pydantic-ai-slim>=2.66,<3` and commit the lockfile. Add provider extras
  only where used; avoid installing every provider SDK in the host.
- Use native `ModelMessage`, `ModelRequest`, `ModelResponse`, `TextPart`,
  `ThinkingPart` and `RequestUsage`. Preserve the native representation of tool and
  multimodal parts without implementing their execution or UI.
- Route chat and the LLM stage of RAG through one bridge. Adapt existing
  role/content input and first-string output; use `generate_result` when supplied,
  or Pydantic AI's direct request API for a native `Model`.
- Retain validation with redacted error messages, tuple support and exactly one
  generation path. Validate snapshots of mutable native messages and responses.
- Preserve session parameters, credential lookup, answer-only storage and history.
  Custom task plugins retain their own legacy input/output path, including text
  task subclasses with customized preparation or output hooks.
  Reject output the current task cannot store instead of silently losing parts.

Acceptance: legacy and enriched chat/RAG jobs pass with the same configuration;
Pydantic AI's `FunctionModel` works without network access or an agent loop;
document/image/audio/video and binary inputs reach capable models unchanged and
fail before generation for legacy models. Test the supported Python minimum too.

## 2. Reasoning and chat: a separate PR

Rebase/adapt the existing reasoning-panel work onto the foundation after coordinating
with its author. Replace provisional provider dictionaries with native
`ThinkingPart`/`TextPart` responses. Read `generation_result` in the RAG task and the
native response in the text task; do not add another result schema.

Store structured messages beside the existing answer using a versioned storage
envelope. Keep existing `str` rows readable, preserve provider fields needed for
later turns and use the native history serializer. Keeping full stored history
does not mean sending all of it: explicitly project the supported parts for each
model. Reasoning display and history-replay policies must remain separate; opaque
provider reasoning may be required for some continuations.

Acceptance: collapsed reasoning in chat and RAG, reasoning-only/partial output
retained with an incomplete indication, old sessions readable, no accidental
reasoning text in ordinary answer history, and no loss of opaque provider fields
in storage. No blanket promise that every model can continue from answer-only
history. Usage can stay stored but hidden until its UI is designed.

## 3. Provider adapters: plugins and local engines

Migrate OpenRouter and Ollama independently in their own repositories, retaining
the existing schema names and credentials. Use native Pydantic AI adapters where
they preserve the required options. Compare parameter mappings, error handling,
timeouts and retries before replacing the current HTTP/SDK paths.

Plugins keep `generate` for older hosts. New host types and provider-specific
imports may be lazy inside `generate_result`; an old host must not need them to
import or run the legacy method. Each path makes one logical generation request.
For in-process GGUF engines, implement an explicit adapter instead of starting a
new server merely to match an HTTP provider.

Acceptance: old/new host and plugin matrix, mock-server tests of parameters and
credentials, and a controlled live smoke test where authorized. Do not enable
provider or agent retries that can repeat a billed generation without reviewing
that behavior. Keep the old parameter configuration intact.

## 4. Attachments and multimodal tasks

Connect existing uploads to native content parts, advertise per-model input/output
capabilities and reject unsupported combinations before generation. Validate file
references and limits at the upload/provider boundary. File contents and private
paths must not leak into validation errors.

Documents can be sent to a capable model or processed by DashAI's RAG pipeline;
these remain distinct workflows. Add image/audio/video output persistence and
rendering before enabling those outputs in chat. Keep explicit adapters for local
Diffusers, ControlNet, transcription and other engines. Traditional training tasks
(classification, regression, clustering and forecasting) retain their interfaces.

Acceptance: at least one supported provider per enabled modality, tests of the
binary/file round trip and provider-specific limits, and existing tasks unchanged.

## Version and rollout policy

The lockfile pins the tested Pydantic AI release; the dependency range excludes its
next major. Review upstream message/provider changes and run the compatibility
suite before changing that range or upgrading the lockfile. Native types are now
a public plugin dependency, so upgrades need coordination with plugin adapters.

There is no user-facing interface-version switch. Detect the enriched method,
keep adapting `generate`, and version persisted structures separately from package
versions. Additive host releases keep accepting old plugin methods; removing that
path is a separately announced incompatible change. No history rewrite is needed
for this foundation PR.

Agent tools, streaming, cancellation and the permission model in
[#974](https://github.com/DashAISoftware/dashAI/issues/974) remain separate work.
Adopting the message contract does not enable automatic tool execution.

References: [direct requests](https://ai.pydantic.dev/direct/),
[native messages](https://ai.pydantic.dev/api/messages/),
[multimodal input](https://ai.pydantic.dev/input/),
[slim installation](https://ai.pydantic.dev/install/).
