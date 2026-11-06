import { useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { Box, Stack } from "@mui/material";
import useFormSchema from "../../../hooks/useFormSchema";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import FormSchemaParameterContainer from "../../shared/FormSchemaParameterContainer";
import FormSchemaRenderFields from "../../shared/FormSchemaRenderFields";
import PromptFieldCard from "./PromptFieldCard";
import RagLlmModelField, { LLM_MODEL_PARENT } from "./RagLlmModelField";
import { isPromptFieldSchema } from "./promptSchema";
import { getSchemaRules } from "../../../utils/schema";
import { evaluateRules } from "../../../utils/ruleEngine";

/** Matches FormSchemaRenderFields' own default spacing. */
const FIELD_SPACING = 1;

/** Shared default so an omitted prop does not allocate a new array per render. */
const EMPTY_FIELDS = [];

/**
 * Whether a schema property is a nested LLM reference.
 *
 * RAG stages that need function calling declare their helper model this way.
 * Matching on the declared parent keeps the special rendering schema-driven,
 * so a renamed field still gets it and non-LLM component fields do not.
 *
 * @param {object} fieldSchema - The property schema to inspect.
 * @returns {boolean} True for a nested text-generation component field.
 */
function isLlmModelFieldSchema(fieldSchema) {
  // Mirror FormSchemaRenderFields' precedence: an optimizer or union field is
  // never rendered by the generic nested-component branch either.
  return Boolean(
    fieldSchema?.type === "object" &&
    fieldSchema?.parent === LLM_MODEL_PARENT &&
    fieldSchema?.placeholder?.optimize === undefined &&
    !fieldSchema?.anyOf,
  );
}

/**
 * Split the renderable schema keys into consecutive runs of prompt, nested LLM
 * and generic fields.
 *
 * Each run is drawn by one renderer — prompt runs as prompt cards, LLM runs as
 * RAG LLM fields, everything else through `FormSchemaRenderFields` — so a
 * special field keeps the position of its own key instead of being hoisted
 * above the rest of the form.
 *
 * @param {string[]} keys - Renderable schema keys, in declaration order.
 * @param {Set<string>} promptKeys - The subset of keys holding a prompt ref.
 * @param {Set<string>} llmKeys - The subset of keys holding a nested LLM ref.
 * @returns {Array<{kind: "prompt"|"llm"|"fields", keys: string[]}>} The ordered
 *   segments.
 */
function buildFieldSegments(keys, promptKeys, llmKeys) {
  const segments = [];

  for (const key of keys) {
    let kind = "fields";
    if (promptKeys.has(key)) {
      kind = "prompt";
    } else if (llmKeys.has(key)) {
      kind = "llm";
    }
    const current = segments[segments.length - 1];
    if (current && current.kind === kind) {
      current.keys.push(key);
    } else {
      segments.push({ kind, keys: [key] });
    }
  }

  return segments;
}

/**
 * Drop-in alternative to `FormSchema` for schemas that declare prompt fields.
 *
 * The schema is walked in declaration order and split into consecutive runs:
 * prompt-typed properties become same-level prompt cards (selector, template
 * preview, create/edit actions) at the exact position of their key, nested
 * text-generation properties become `RagLlmModelField` (which seeds the model
 * with the owner's function-calling budget), and every other run is delegated
 * to `FormSchemaRenderFields`, so optimizers, unions, nested component
 * references, relevance rules and autosave behave exactly as they do in
 * `FormSchema`. Any schema therefore gains the richer prompt editor without
 * per-schema code.
 *
 * @param {object}   props
 * @param {string}   props.model - The configurable object to render.
 * @param {object}   [props.initialValues] - Values the form starts from.
 * @param {Function} [props.onFormSubmit] - Receives all form values.
 * @param {boolean}  [props.autoSave] - Submits on every change when true.
 * @param {Function} [props.onCancel] - Cancel button handler.
 * @param {object}   [props.formSubmitRef] - Ref receiving the formik object.
 * @param {boolean}  [props.error] - External error state for the actions.
 * @param {Function} [props.setError] - Reports whether the form has errors.
 * @param {object}   [props.errorsMessage] - Per-field error messages.
 * @param {string}   [props.saveButtonText] - Save button label override.
 * @param {Function} [props.onValuesChange] - Called when values change.
 * @param {boolean}  [props.showBorder] - Wraps the body in a bordered box.
 * @param {boolean}  [props.hideButtons] - Hides the action row.
 * @param {string[]} [props.excludeFields] - Fields the caller renders itself.
 * @param {Function} [props.promptFilter] - `(fieldName, option) => boolean`
 *   deciding which prompt components a prompt field offers.
 * @returns {JSX.Element} The schema form with prompt cards.
 */
function FormSchemaWithPrompts({
  model,
  initialValues,
  onFormSubmit,
  autoSave,
  onCancel,
  formSubmitRef,
  error,
  setError,
  errorsMessage,
  saveButtonText,
  onValuesChange,
  showBorder = true,
  hideButtons = false,
  excludeFields = EMPTY_FIELDS,
  promptFilter,
}) {
  const { formik, modelSchema, handleUpdateSchema } = useFormSchema({
    model,
    initialValues,
    formSubmitRef,
    setError,
    onValuesChange,
  });

  // Renderable keys in declaration order: what the caller excluded is gone, and
  // everything that is left keeps the schema's own order.
  const orderedKeys = useMemo(() => {
    if (!modelSchema) return EMPTY_FIELDS;
    return Object.keys(modelSchema).filter(
      (key) => !excludeFields.includes(key),
    );
  }, [modelSchema, excludeFields]);

  const promptKeys = useMemo(
    () => orderedKeys.filter((key) => isPromptFieldSchema(modelSchema?.[key])),
    [orderedKeys, modelSchema],
  );

  const llmModelKeys = useMemo(
    () =>
      orderedKeys.filter((key) => isLlmModelFieldSchema(modelSchema?.[key])),
    [orderedKeys, modelSchema],
  );

  const segments = useMemo(
    () =>
      buildFieldSegments(
        orderedKeys,
        new Set(promptKeys),
        new Set(llmModelKeys),
      ),
    [orderedKeys, promptKeys, llmModelKeys],
  );

  // The same relevance pass `FormSchemaRenderFields` runs for every other
  // field: a prompt card or nested LLM has to honour "hide"/"omit" and
  // "disable" too, or a rule that hides one would only apply to whatever
  // renders it next.
  const relevance = useMemo(
    () =>
      evaluateRules(getSchemaRules(modelSchema), formik?.values ?? {})
        .relevance,
    [modelSchema, formik?.values],
  );

  /**
   * Resolve the presentation a special field shares across renderers.
   *
   * @param {string} key - The field name.
   * @returns {{fieldSchema: object, description: string|undefined,
   *   disabled: boolean}|null} Null when a relevance rule hides the field.
   */
  const fieldPresentation = (key) => {
    const fieldState = relevance[key];
    const isIrrelevant = fieldState !== undefined && !fieldState.relevant;
    // "hide" and "omit" both mean "do not render"; "disable" keeps the field
    // visible but inert and explains the rule underneath it.
    if (isIrrelevant && fieldState.effect !== "disable") return null;
    const disabled = isIrrelevant && fieldState.effect === "disable";

    const fieldSchema = modelSchema[key];
    const description =
      disabled && fieldState.reason
        ? `${fieldSchema.description ?? ""}\n\n_${fieldState.reason}_`
        : fieldSchema.description;

    return { fieldSchema, description, disabled };
  };

  /**
   * Store a prompt or nested LLM value and let the form report the change.
   *
   * @param {string} key - The field name.
   * @param {object} value - The canonical `{component, params}` reference.
   */
  const handleEmbeddedFieldChange = useCallback(
    (key, value) => {
      formik.setFieldValue(key, value, true);
      handleUpdateSchema(
        { ...formik.values, [key]: value },
        autoSave ? onFormSubmit : null,
      );
    },
    [formik, handleUpdateSchema, autoSave, onFormSubmit],
  );

  /**
   * Draw one prompt field, or nothing when the schema rules take it away.
   *
   * @param {string} key - The prompt field name.
   * @returns {JSX.Element|null} The prompt card.
   */
  const renderPromptCard = (key) => {
    const presentation = fieldPresentation(key);
    if (!presentation) return null;
    const { fieldSchema, description, disabled } = presentation;

    return (
      <PromptFieldCard
        key={key}
        name={key}
        paramJsonSchema={fieldSchema}
        description={description}
        disabled={disabled}
        field={{
          value: formik.values?.[key],
          error: formik.errors?.[key],
          onChange: (value) => handleEmbeddedFieldChange(key, value),
        }}
        promptFilter={promptFilter}
      />
    );
  };

  /**
   * Draw one nested LLM field, or nothing when the schema rules take it away.
   *
   * @param {string} key - The field name.
   * @returns {JSX.Element|null} The RAG LLM field.
   */
  const renderLlmModelField = (key) => {
    const presentation = fieldPresentation(key);
    if (!presentation) return null;
    const { fieldSchema, description, disabled } = presentation;
    const fieldError = formik.errors?.[key];
    const errorMessage =
      errorsMessage?.[key]?.message ??
      (typeof fieldError === "string" ? fieldError : fieldError?.message);

    return (
      <RagLlmModelField
        key={key}
        ownerComponent={model}
        value={formik.values?.[key]}
        onChange={(value) => handleEmbeddedFieldChange(key, value)}
        label={fieldSchema.title}
        description={description}
        errorMessage={errorMessage}
        disabled={disabled}
        required={Boolean(fieldSchema.required)}
      />
    );
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        minHeight: 0,
      }}
    >
      <FormSchemaParameterContainer showBorder={showBorder}>
        <Stack spacing={FIELD_SPACING}>
          {segments.map((segment) => {
            if (segment.kind === "prompt") {
              return segment.keys.map((key) => renderPromptCard(key));
            }
            if (segment.kind === "llm") {
              return segment.keys.map((key) => renderLlmModelField(key));
            }
            return (
              <FormSchemaRenderFields
                key={`fields-${segment.keys[0]}`}
                modelSchema={modelSchema}
                formik={formik}
                autoSave={autoSave}
                handleUpdateSchema={handleUpdateSchema}
                onFormSubmit={onFormSubmit}
                setError={setError}
                errorsMessage={errorsMessage}
                // Only this run's keys: the renderer keeps its own relevance,
                // disable, optimizer, union and nested-component behaviour.
                excludeFields={[
                  ...excludeFields,
                  ...orderedKeys.filter((key) => !segment.keys.includes(key)),
                ]}
              />
            );
          })}
        </Stack>
      </FormSchemaParameterContainer>

      {!hideButtons && (
        <FormSchemaButtonGroup
          onCancel={onCancel}
          onFormSubmit={onFormSubmit}
          autoSave={autoSave}
          formik={formik}
          error={error}
          saveButtonText={saveButtonText}
        />
      )}
    </Box>
  );
}

FormSchemaWithPrompts.propTypes = {
  model: PropTypes.string,
  initialValues: PropTypes.object,
  onFormSubmit: PropTypes.func,
  autoSave: PropTypes.bool,
  onCancel: PropTypes.func,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }),
  error: PropTypes.bool,
  setError: PropTypes.func,
  errorsMessage: PropTypes.object,
  saveButtonText: PropTypes.string,
  onValuesChange: PropTypes.func,
  showBorder: PropTypes.bool,
  hideButtons: PropTypes.bool,
  excludeFields: PropTypes.arrayOf(PropTypes.string),
  promptFilter: PropTypes.func,
};

export default FormSchemaWithPrompts;
