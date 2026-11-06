import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import FormSchema from "../../shared/FormSchema";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { DescriptionBlock } from "../../shared/FormSchemaFieldCard";
import ComponentDownloadControl from "../../models/model/ComponentDownloadControl";
import useModelParents from "../../../hooks/useModelParents";
import { resolveLocalizedText } from "../../../utils/localize";
import {
  getModelFromSubform,
  getParamsFromSubform,
} from "../../../utils/schema";
import { resolveRagLlmDefaults } from "../../../pages/generative/RAGSession/advanced/resolveRagLlmDefaults";

/** Parent class every text-generation component shares in the registry. */
export const LLM_MODEL_PARENT = "TextToTextGenerationTaskModel";

/** Stable empty params, so an absent carried map keeps a stable identity. */
const EMPTY_PARAMS = {};

/**
 * Drop empty values from an LLM parameter map.
 *
 * A cleared control reports `""` or `null`, which a non-nullable numeric
 * parameter rejects on save. Omitting the key lets the backend resolve the
 * parameter again, exactly as the query-transformation editor does.
 *
 * @param {object} values - Parameters collected by the nested form.
 * @returns {object} The parameters worth persisting.
 */
function paramsToPersist(values) {
  const result = {};
  for (const [key, value] of Object.entries(values || {})) {
    if (value === "" || value === null || value === undefined) continue;
    result[key] = value;
  }
  return result;
}

/**
 * Schema card for a RAG stage's nested LLM reference.
 *
 * The shared nested-component picker seeds a newly selected component from its
 * own schema. That is the right default everywhere else, but the helper LLMs
 * of a RAG retriever (and of the query-transformation stage) need the
 * function-calling budget the owning schema declares: a context window large
 * enough for the prompt plus its chunks and a completion budget that fits the
 * structured call. This field resolves those owner-declared overrides through
 * `resolveRagLlmDefaults`, so selecting another LLM keeps the stage usable
 * instead of silently falling back to the text-generation placeholders.
 *
 * It is intentionally RAG-local: the shared form components stay untouched,
 * and no other nested component field changes behaviour.
 *
 * @param {object}   props
 * @param {string}   props.ownerComponent - Registered name of the retriever or
 *   transformer that declares the `llm_model` field.
 * @param {object}   [props.value] - The stored `{component, params}` reference
 *   (or the legacy subform shape).
 * @param {Function} props.onChange - Receives the canonical reference.
 * @param {string}   [props.label] - Field label shown above the selector.
 * @param {string}   [props.description] - Field description.
 * @param {string}   [props.errorMessage] - Validation message for the field.
 * @param {boolean}  [props.disabled] - Renders the selector and form inert.
 * @param {boolean}  [props.required] - Marks the selector as required.
 * @returns {JSX.Element} The LLM selector and its parameter form.
 */
export default function RagLlmModelField({
  ownerComponent,
  value,
  onChange,
  label,
  description,
  errorMessage,
  disabled = false,
  required = false,
}) {
  const { t, i18n } = useTranslation(["generative"]);
  const { models, markDownloaded } = useModelParents({
    parent: LLM_MODEL_PARENT,
  });

  const valueComponent = getModelFromSubform(value);
  const carriedParams = useMemo(
    () => getParamsFromSubform(value) ?? {},
    [value],
  );

  const [selectedName, setSelectedName] = useState(valueComponent);
  const [seedDefaults, setSeedDefaults] = useState(null);
  const seedRequestRef = useRef(0);
  const seededKeyRef = useRef(null);
  // A -> B -> A must restore A's edited parameters, not reseed them.
  const rememberedParamsRef = useRef(new Map());

  // A parent-driven value change (form reset, session reload) wins over the
  // local selection used while an async seed is still resolving. Bump the
  // request id when it differs from the pending selection so a late seed
  // cannot re-apply the selection the parent just replaced.
  useEffect(() => {
    if (valueComponent !== selectedName) {
      seedRequestRef.current += 1;
    }
    setSelectedName(valueComponent);
    // `selectedName` is intentionally not a dependency: it changes when the
    // user selects, and adding it would cancel that selection's own request.
  }, [valueComponent]);

  /**
   * Resolve the RAG seed for one LLM, ignoring results superseded by a newer
   * request. The owner key lets the mount effect skip re-fetching a seed the
   * selection handler already resolved.
   *
   * @param {string} name - Registered LLM component name.
   * @returns {Promise<object|null>} The seed, or null when superseded.
   */
  const resolveSeed = useCallback(
    async (name) => {
      const requestId = seedRequestRef.current + 1;
      seedRequestRef.current = requestId;
      try {
        const defaults = await resolveRagLlmDefaults(ownerComponent, name);
        if (requestId !== seedRequestRef.current) return null;
        seededKeyRef.current = `${ownerComponent}::${name}`;
        return defaults || {};
      } catch (error) {
        console.warn(
          `[RagLlmModelField] Could not resolve the defaults of ${name}:`,
          error,
        );
        if (requestId !== seedRequestRef.current) return null;
        seededKeyRef.current = `${ownerComponent}::${name}`;
        return {};
      }
    },
    [ownerComponent],
  );

  // Seed the form for the stored selection too: the saved ref may carry only
  // some parameters, and the missing ones still need the RAG budget.
  useEffect(() => {
    if (!valueComponent) {
      seededKeyRef.current = null;
      setSeedDefaults({});
      return undefined;
    }
    if (seededKeyRef.current === `${ownerComponent}::${valueComponent}`) {
      return undefined;
    }

    // A parent-driven change starts a new model: hide the old model's form
    // until its own seed arrives, so no foreign parameter is editable.
    setSeedDefaults(null);
    let cancelled = false;
    resolveSeed(valueComponent).then((seed) => {
      if (!cancelled && seed) setSeedDefaults(paramsToPersist(seed));
    });
    return () => {
      cancelled = true;
    };
  }, [ownerComponent, valueComponent, resolveSeed]);

  /**
   * Select another LLM, persist the selection immediately and replace its
   * placeholder params with the RAG seed once that resolves.
   *
   * @param {object} event - Select change event.
   * @returns {Promise<void>} Resolves once the parent value has been updated.
   */
  const handleModelChange = async (event) => {
    const name = event.target.value;
    if (!name) return;

    if (valueComponent && valueComponent !== name) {
      rememberedParamsRef.current.set(valueComponent, carriedParams);
    }
    const remembered = rememberedParamsRef.current.get(name);

    setSelectedName(name);
    setSeedDefaults(null);

    // Persist the selected component before the seed arrives. The modal that
    // hosts this field can be saved in the meantime; without this write the
    // node would keep the previous LLM and the panel would stay clean. The
    // seed replaces the placeholder params as soon as it resolves.
    seededKeyRef.current = `${ownerComponent}::${name}`;
    onChange({
      component: name,
      params: remembered ? paramsToPersist(remembered) : {},
    });

    const seed = await resolveSeed(name);
    if (seed === null) return;

    const persistedSeed = paramsToPersist(seed);
    const params = remembered
      ? paramsToPersist({ ...persistedSeed, ...remembered })
      : persistedSeed;
    setSeedDefaults(persistedSeed);
    onChange({ component: name, params });
  };

  const selectedComponent = models?.find(
    (model) => model.name === selectedName,
  );
  // While the parent still holds the previous model, its params belong to that
  // model: merging them would briefly show the wrong values for the new one.
  let carriedForSelection = EMPTY_PARAMS;
  if (selectedName === valueComponent) {
    carriedForSelection = carriedParams;
  }
  const initialValues = useMemo(
    () => ({ ...(seedDefaults || {}), ...carriedForSelection }),
    [seedDefaults, carriedForSelection],
  );
  const formReady = Boolean(selectedName) && seedDefaults !== null;
  const selectedNameIsListed =
    !selectedName ||
    (models || []).some((model) => model.name === selectedName);
  const modelLabel = (model) =>
    resolveLocalizedText(model.display_name, i18n) || model.name;

  return (
    <Stack spacing={1}>
      <TextField
        select
        size="small"
        fullWidth
        label={label}
        value={selectedName || ""}
        onChange={handleModelChange}
        disabled={disabled || !models}
        error={Boolean(errorMessage)}
        required={required}
      >
        {(models || []).map((model) => (
          <MenuItem key={model.name} value={model.name}>
            {modelLabel(model)}
          </MenuItem>
        ))}
        {selectedName && !selectedNameIsListed && (
          <MenuItem value={selectedName}>{selectedName}</MenuItem>
        )}
      </TextField>

      {!models && (
        <Typography variant="caption" color="text.secondary">
          {t("generative:rag.common.loading")}
        </Typography>
      )}

      {selectedName && seedDefaults === null && <LinearProgress />}

      {(errorMessage || description) && (
        <DescriptionBlock
          text={errorMessage ?? description}
          isError={Boolean(errorMessage)}
        />
      )}

      <Box
        component="fieldset"
        disabled={disabled}
        sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}
      >
        {selectedComponent?.metadata?.requires_download && (
          <Box>
            <ComponentDownloadControl
              component={selectedComponent}
              onStatusChange={(isDownloaded) =>
                markDownloaded(selectedComponent.name, isDownloaded)
              }
            />
          </Box>
        )}

        {formReady && (
          <FormSchemaContainer key={`rag-llm-form-${selectedName}`}>
            <FormSchema
              autoSave
              hideButtons
              model={selectedName}
              initialValues={initialValues}
              onFormSubmit={(values) =>
                onChange({
                  component: selectedName,
                  params: paramsToPersist(values),
                })
              }
            />
          </FormSchemaContainer>
        )}
      </Box>
    </Stack>
  );
}

RagLlmModelField.propTypes = {
  ownerComponent: PropTypes.string.isRequired,
  value: PropTypes.object,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string,
  description: PropTypes.string,
  errorMessage: PropTypes.string,
  disabled: PropTypes.bool,
  required: PropTypes.bool,
};
