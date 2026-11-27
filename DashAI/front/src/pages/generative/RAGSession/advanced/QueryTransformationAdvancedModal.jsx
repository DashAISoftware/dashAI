import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import { Button, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  QUERY_TRANSFORMATION_BLOCK,
  isCompleteQueryTransformationRef,
  isGeneratorDownloaded,
  resolveLabel,
  stageParams,
} from "../../../../utils/ragQueryTransformation";
import {
  LLM_MODEL_KEY,
  MAX_SUBQUERIES_KEY,
  RERANKER_KEY,
} from "../../../../constants/rag";
import FormSchema from "../../../../components/shared/FormSchema";
import FormSchemaWithPrompts from "../../../../components/generative/RAG/FormSchemaWithPrompts";
import FormSchemaContainer from "../../../../components/shared/FormSchemaContainer";
import RAGAdvancedDialog from "../../../../components/shared/RAGAdvancedDialog";
import { resolveRagLlmDefaults } from "./resolveRagLlmDefaults";

/**
 * Transformer params that keep their specialized control instead of being
 * rendered by the generic schema form: the nested LLM model. The prompt and the
 * optional reranker are schema fields now, drawn by the generic form (a prompt
 * card and a component field).
 */
const TRANSFORMER_EXCLUDED_FIELDS = [LLM_MODEL_KEY];

/**
 * Transformer params whose cleared value is a choice the backend understands
 * rather than an omission: `max_subqueries: null` means "no limit" and
 * `reranker: null` means "no reranking", so the key is persisted as an explicit
 * null. Dropping it would let the schema placeholder reinstate the default.
 */
const NULLABLE_TRANSFORMER_FIELDS = [MAX_SUBQUERIES_KEY, RERANKER_KEY];

/**
 * Decide which of the transformation LLM's parameter values a form submission
 * must persist.
 *
 * The stage's nested LLM params are merged backend-side as
 * `{...schema_defaults, ...rag_overrides, ...caller_params}`, where
 * `rag_overrides` are the RAG defaults the transformer schema pins in
 * `llm_model.placeholder.params` (a tight context window and temperature).
 * So the form must only ever send the keys the user actually meant to set:
 *
 *  - A cleared field is dropped, so the backend re-resolves it.
 *  - A key that was already in the carried ref is always echoed, even when it
 *    equals the seed value: it is a user choice this edit must not lose.
 *  - Any other key still equal to its seed value is left out, so a freshly
 *    enabled stage does not smuggle the seed over the backend's own
 *    resolution of the same RAG defaults.
 *
 * @param {object} carriedParams The ref's params captured when the form was
 *   seeded, i.e. what the user had stored before this edit.
 * @param {object} seedDefaults The seed values: the LLM's schema defaults with
 *   the transformer's RAG overrides applied.
 * @param {object} values The complete values FormSchema hands back.
 * @returns {object} The params to persist for `llm_model`.
 */
function llmParamsToPersist(carriedParams, seedDefaults, values) {
  const result = {};

  for (const key of Object.keys(values)) {
    const value = values[key];
    if (value === "" || value === null || value === undefined) continue;

    const wasCarried = Object.prototype.hasOwnProperty.call(carriedParams, key);
    const isUntouchedDefault =
      JSON.stringify(value) === JSON.stringify(seedDefaults[key]);
    if (!wasCarried && isUntouchedDefault) continue;

    result[key] = value;
  }

  return result;
}

/**
 * Full-reference editor for the query transformation stage.
 *
 * Mirrors `RetrieverAdvancedModal`'s dialog conventions. Both the transformer's
 * own scalar parameters and the nested LLM's parameters are rendered from the
 * backend schema, exactly like the generator's advanced configuration, so no
 * parameter is hand-rolled and every field the schema declares stays in sync
 * with the server. The transformer form uses `FormSchemaWithPrompts`, so its
 * prompt field is a prompt card; only the nested LLM keeps a specialized
 * select and is excluded from the generic form.
 *
 * @param {object}   props
 * @param {boolean}  props.open - Whether the dialog is open.
 * @param {Function} props.onClose - Closes the dialog.
 * @param {object}   props.model - The current stage ref `{component, params}`.
 *   The picker mounts the modal only while the stage is on, so it always has one.
 * @param {Function} props.setModel - Persists the edited ref.
 * @param {string}   [props.technique] - The transformer's technique, deciding
 *   which parameters apply.
 * @param {Array}    props.generators - Generator models for the model select.
 * @returns {JSX.Element} The advanced query transformation modal.
 */
export default function QueryTransformationAdvancedModal({
  open,
  onClose,
  model,
  setModel,
  technique,
  generators,
}) {
  const { t } = useTranslation(["generative"]);
  const [params, setParams] = useState(stageParams(model));
  const [seededCarried, setSeededCarried] = useState(null);
  const [seedDefaults, setSeedDefaults] = useState(null);
  const [seedError, setSeedError] = useState(null);

  // Refs mirror the seed state so the submit handler never reads a stale
  // closure: autosave rewrites `params` on every keystroke, but the carried
  // baseline must stay whatever it was when the form mounted.
  const carriedParamsRef = useRef({});
  const seedDefaultsRef = useRef({});

  // Start from the persisted reference each time the dialog opens; while it is
  // open the edits live here and only reach the session on Done.
  useEffect(() => {
    if (open) setParams(stageParams(model));
  }, [open, model]);

  const promptOptionsFilter = useCallback(
    (_fieldName, option) =>
      !technique || option.metadata?.technique === technique,
    [technique],
  );

  /**
   * Merges the transformer's schema values into the stage params.
   * `llm_model` is edited by its own control, so it is left untouched; a
   * cleared scalar is dropped so the backend re-resolves it, except for the
   * nullable ones whose cleared state is an explicit choice (`max_subqueries`
   * cleared means "no limit"). The prompt now arrives as the canonical
   * `{component, params}` reference and is stored as such.
   */
  const handleTransformerFormSubmit = (values) =>
    setParams((prev) => {
      const next = { ...prev };
      for (const key of Object.keys(values)) {
        if (TRANSFORMER_EXCLUDED_FIELDS.includes(key)) continue;
        const value = values[key];
        if (value === "" || value === null || value === undefined) {
          if (NULLABLE_TRANSFORMER_FIELDS.includes(key)) {
            next[key] = null;
          } else {
            delete next[key];
          }
        } else {
          next[key] = value;
        }
      }
      return next;
    });

  /**
   * The params the stored stage carries for the nested LLM `name`, so that
   * switching away from it and back restores them.
   * @param {string} key - The nested component parameter.
   * @param {string} name - The component being selected.
   * @returns {object} The carried params, or an empty map when nothing is
   *   carried for that component (the backend then resolves the RAG defaults).
   */
  const carriedParamsFor = (key, name) => {
    if (key !== LLM_MODEL_KEY) return {};
    const stored = stageParams(model)[LLM_MODEL_KEY];
    if (stored?.component !== name) return {};
    return stored.params;
  };

  /** Points a nested component parameter at `name`, keeping its params on reselect. */
  const setComponent = (key, name) =>
    setParams((prev) => {
      const next = { ...prev };
      if (!name) {
        delete next[key];
        return next;
      }
      // A -> B -> A must not lose A's saved params: switching away replaced the
      // live map, so restore the original component's carried values when the
      // user returns to it. A different model starts empty and lets the
      // backend resolve the RAG defaults for it.
      if (prev[key]?.component === name) {
        next[key] = { component: name, params: prev[key].params };
        return next;
      }
      next[key] = {
        component: name,
        params: { ...carriedParamsFor(key, name) },
      };
      return next;
    });

  const llmComponent = params[LLM_MODEL_KEY]?.component;

  // Seed the schema form for the selected LLM with the RAG defaults the
  // transformer schema declares, not the LLM's generic placeholders: that is
  // the budget the backend actually resolves, so showing anything else would
  // both mislead and be persisted on the next edit. What the ref carried at
  // this instant decides the emission mode for the whole editing session: an
  // empty map means the backend must keep re-resolving the defaults it owns.
  // The baseline is read from the `model` prop (the pre-edit source of truth)
  // and re-captured on every dialog open, so a previously saved empty ref can
  // never be misremembered as a carried one. If the user switched to a
  // different LLM, nothing is carried for it: its untouched values must not be
  // pinned over the backend's own RAG overrides.
  useEffect(() => {
    if (!llmComponent) {
      carriedParamsRef.current = {};
      seedDefaultsRef.current = {};
      setSeededCarried(null);
      setSeedDefaults(null);
      setSeedError(null);
      return undefined;
    }

    const carried = carriedParamsFor(LLM_MODEL_KEY, llmComponent);
    carriedParamsRef.current = carried;
    seedDefaultsRef.current = {};
    setSeededCarried(carried);
    setSeedDefaults(null);

    setSeedError(null);

    let cancelled = false;
    resolveRagLlmDefaults(model.component, llmComponent)
      .then((defaults) => {
        if (cancelled) return;
        seedDefaultsRef.current = defaults;
        setSeedDefaults(defaults);
      })
      .catch((error) => {
        if (cancelled) return;
        setSeedError(error instanceof Error ? error.message : String(error));
      });

    return () => {
      cancelled = true;
    };
    // Keyed on the open flag, the model prop and the component only: the
    // carried baseline is captured here, so it must not re-run when autosave
    // rewrites the modal's live params.
  }, [open, model, llmComponent]);

  // Start from the RAG seed, then let carried/live values win. A partially
  // saved ref (for example only `temperature`) must not fall back to the
  // model's generic placeholders for the keys it does not carry: those keys
  // still need the RAG 10K/300 defaults. The carried baseline is used rather
  // than only the live params because switching away and back resets the live
  // map, while the original values must still be restored.
  const liveLlmParams = params[LLM_MODEL_KEY]?.params;
  const llmInitialValues = useMemo(() => {
    if (!llmComponent) return {};
    return {
      ...seedDefaults,
      ...seededCarried,
      ...liveLlmParams,
    };
  }, [llmComponent, seededCarried, liveLlmParams, seedDefaults]);

  // Always wait for the RAG seed: a carried partial map is not enough to fill
  // the keys it omits.
  const llmFormReady = Boolean(llmComponent) && seedDefaults !== null;

  /** Maps the schema form's full value set onto the params to persist. */
  const handleLlmFormSubmit = (values) =>
    setParams((prev) => {
      if (!prev[LLM_MODEL_KEY]) return prev;
      return {
        ...prev,
        [LLM_MODEL_KEY]: {
          component: prev[LLM_MODEL_KEY].component,
          params: llmParamsToPersist(
            carriedParamsRef.current,
            seedDefaultsRef.current,
            values,
          ),
        },
      };
    });

  const [retrieversComplete, setRetrieversComplete] = useState(true);
  const refComplete = isCompleteQueryTransformationRef({ params });
  const llmDownloaded = isGeneratorDownloaded(generators, llmComponent);
  const complete =
    refComplete && llmDownloaded && retrieversComplete && seedError === null;

  const llmOptions = generators.filter(
    (generator) => generator.downloaded || generator.name === llmComponent,
  );

  /**
   * The i18n key suffix of what keeps the stage from being saved.
   * @returns {string|null} The key under `rag.config.queryTransformation`, or
   *   null when the stage is complete.
   */
  const incompleteReason = () => {
    if (!refComplete) return QUERY_TRANSFORMATION_BLOCK.INCOMPLETE;
    if (!llmDownloaded)
      return QUERY_TRANSFORMATION_BLOCK.NEEDS_DOWNLOADED_MODEL;
    if (!retrieversComplete)
      return QUERY_TRANSFORMATION_BLOCK.COMPOSITE_INCOMPLETE;
    return null;
  };
  const reason = incompleteReason();

  const handleDone = () => {
    if (!complete) return;
    setModel({ component: model.component, params });
    onClose();
  };

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={t("generative:rag.config.queryTransformation.advanced")}
      minHeight={400}
      actions={
        <>
          <Button onClick={onClose} variant="outlined">
            {t("generative:rag.advanced.close")}
          </Button>
          <Button
            onClick={handleDone}
            variant="contained"
            color="primary"
            disabled={!complete}
          >
            {t("generative:rag.advanced.done")}
          </Button>
        </>
      }
    >
      <Stack spacing={2} sx={{ pt: 1 }}>
        <Typography variant="caption" color="text.secondary">
          {model.component}
        </Typography>

        {reason && (
          <Typography variant="caption" color="error.main">
            {t(`generative:rag.config.queryTransformation.${reason}`)}
          </Typography>
        )}

        {seedError !== null && (
          <Typography variant="caption" color="error.main">
            {t("generative:rag.config.queryTransformation.loadFailed", {
              reason: seedError,
            })}
          </Typography>
        )}

        <TextField
          select
          size="small"
          label={t("generative:rag.config.queryTransformation.llm")}
          value={params[LLM_MODEL_KEY]?.component ?? ""}
          onChange={(event) => setComponent(LLM_MODEL_KEY, event.target.value)}
        >
          {llmOptions.map((generator) => (
            <MenuItem key={generator.name} value={generator.name}>
              {resolveLabel(generator.display_name, generator.name)}
            </MenuItem>
          ))}
        </TextField>

        {llmFormReady && (
          <FormSchemaContainer key={`llm-form-${llmComponent}`}>
            <FormSchema
              autoSave
              hideButtons
              model={llmComponent}
              initialValues={llmInitialValues}
              onFormSubmit={handleLlmFormSubmit}
            />
          </FormSchemaContainer>
        )}

        {model.component && (
          <FormSchemaContainer key={`transformer-form-${model.component}`}>
            <FormSchemaWithPrompts
              autoSave
              hideButtons
              model={model.component}
              initialValues={stageParams(model)}
              excludeFields={TRANSFORMER_EXCLUDED_FIELDS}
              promptFilter={promptOptionsFilter}
              onFormSubmit={handleTransformerFormSubmit}
              onRetrieversCompleteChange={setRetrieversComplete}
            />
          </FormSchemaContainer>
        )}
      </Stack>
    </RAGAdvancedDialog>
  );
}

QueryTransformationAdvancedModal.propTypes = {
  open: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  model: PropTypes.object.isRequired,
  setModel: PropTypes.func.isRequired,
  technique: PropTypes.string,
  generators: PropTypes.array.isRequired,
};
