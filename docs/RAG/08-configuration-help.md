# Configuration Help

The RAG session configuration panel exposes five pipeline sections — chunking,
query transformation, retrieval, generation model, and prompt. Each section has
a small **question-mark button** beside its accordion toggle. The button opens a
modal that explains the stage, recommends configurations, names the selected
component, and documents the parameters that component actually exposes.

The help is intentionally **read-only**. It never edits, saves, or re-indexes a
session.

## Where it lives

| File | Role |
| --- | --- |
| `DashAI/front/src/components/generative/RAG/RAGConfigPanel.jsx` | Renders the accordion headers, the help button, and wires the dialog to the active section. |
| `DashAI/front/src/components/generative/RAG/RAGSectionHelpDialog.jsx` | Builds the modal body from the resolved section and the localized help bundle. |
| `DashAI/front/src/utils/i18n/locales/{en,es,pt,de,zh}/generative.json` | `rag.help` translations: labels, stage explanations, recommendations, and parameter explanations. |

The dialog reuses `RAGAdvancedDialog`, the same shell as the advanced chunking,
retriever, generator, and query-transformation editors. This keeps the title
row, close affordance, scroll owner, and footer action consistent with the rest
of the RAG UI.

## Interaction

- The help button is a **sibling of `AccordionSummary`**, not a child. Clicking
  it cannot toggle the accordion.
- The button's accessible name is intentionally generic (`About this section`);
  its `aria-describedby` points at the section title, and the tooltip names the
  section ("About Chunking").
- Opening one section's help closes any other section's help: the panel keeps a
  single `helpSection` state.
- Switching sessions or reloading the configuration clears `helpSection`, so a
  modal cannot reappear on a different session.
- The dialog is responsive: `90vw` on extra-small screens, `85vw` on small
  screens, and `60vw` from medium up, capped at `1100px`. This approximates the
  width of the centre chat panel in the three-panel layout.

## Content order

Every section renders the same blocks in the same order:

1. **Unsaved-changes notice** (only when the section has pending edits).
2. **How it works** — what the stage does. For a disabled optional stage
   (query transformation), an extra note explains that it is currently off.
3. **Recommendations** — configuration guidance. Every recommendation explains
   the available options through the cases where each is more suitable and/or
   the tradeoffs they represent (precision vs. context, coverage vs. noise,
   latency vs. quality, local vs. external models, and so on).
4. **Component** — the selected component's display name and description, when
   available. A disabled query-transformation stage has no component, so this
   block is omitted.
5. **Main parameters** — the parameters the selected component actually exposes.

The order is implemented in `RAGSectionHelpDialog.jsx`; the translations only
provide the strings.

## Parameter explanations

`RAGSectionHelpDialog` does **not** invent parameters. It reads
`section.params` from the backend-resolved configuration and:

1. de-duplicates by `name`,
2. puts the parameters listed in the `KEY_PARAMETERS` constant first, in that
   order, but only when the component actually exposes them,
3. appends any remaining parameters in the backend's order.

Each parameter explanation is resolved as:

1. the curated `rag.help.parameterHelp.<name>` translation,
2. the backend-localized schema `description`,
3. the `rag.help.noDescription` fallback.

Curated help currently covers the highest-traffic parameters: `chunk_size`,
`chunk_overlap`, `top_k`, `temperature`, `max_tokens`, `context_window`,
`device`, `template`, `language`, `history_window`, `n_queries`,
`max_subqueries`, `enable_retrieve_then_expand`, `expand_window`, `prompt`, and
`llm_model`.

When `section.params` is empty — for example, query transformation is disabled
by default — the dialog shows `rag.help.noParameters` instead of fabricating
entries.

## Unsaved changes

The dialog describes the **saved** configuration, because the backend resolves
component names, schema labels, and parameter descriptions for the persisted
session. If the section has unsaved edits, the panel passes `dirty` to the
dialog and the modal shows an informational alert:

> This section has unsaved changes. This explanation describes the saved
> configuration; save your changes to update it.

This keeps the explanation honest without requiring a second endpoint that
resolves arbitrary draft component references.

## Localization

All help copy lives under `rag.help` in the five locale files. The section keys
mirror the RAG parameter keys:

- `chunking_model`
- `query_transformation`
- `retriever_model`
- `generation_model`
- `prompt`

Each section provides `what`, `recommendations` (an array), and — for query
transformation — `disabled`. Shared strings (`title`, `component`,
`howItWorks`, `recommendations`, `parameters`, `noParameters`,
`noDescription`, `dismiss`, `unsaved`) and the `parameterHelp` /
`parameterLabels` maps live beside them.

## Verification

The feature is frontend-only. The project policy for frontend changes is
build-only verification:

- `yarn build` (Create React App, `DISABLE_ESLINT_PLUGIN=true`) must exit 0.
- Scoped `eslint` on the two JSX files must pass.
- Every locale JSON must parse and keep the same `rag.help` key structure.

No frontend automated tests are added or run for this feature.

## Known follow-ups

- The five help buttons share the accessible name "About this section". A unique
  name ("About Chunking", etc.) would be better, but it requires updating the
  existing accordion-header test selectors.
- `KEY_PARAMETERS` duplicates part of the pipeline-key vocabulary already in
  `RAGConfigPanel.jsx`; consolidating both into one shared module would prevent
  drift.
- `parameterHelp` is keyed by bare parameter name. No collision exists today,
  but namespacing by section would make same-named parameters in different
  stages safe.
- The dialog unmounts immediately on close instead of letting MUI play the exit
  transition. Focus restoration still works; the missing animation is cosmetic.
