import { useCallback, useMemo } from "react";
import PropTypes from "prop-types";
import { Box, Stack } from "@mui/material";
import useFormSchema from "../../../hooks/useFormSchema";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import FormSchemaParameterContainer from "../../shared/FormSchemaParameterContainer";
import FormSchemaRenderFields from "../../shared/FormSchemaRenderFields";
import PromptFieldCard from "./PromptFieldCard";
import { isPromptFieldSchema } from "./promptSchema";
import { getSchemaRules } from "../../../utils/schema";
import { evaluateRules } from "../../../utils/ruleEngine";

/** Matches FormSchemaRenderFields' own default spacing. */
const FIELD_SPACING = 1;

/** Shared default so an omitted prop does not allocate a new array per render. */
const EMPTY_FIELDS = [];

/**
 * Split the renderable schema keys into consecutive runs of prompt and
 * non-prompt fields.
 *
 * Each run is drawn by one renderer — prompt runs as prompt cards, everything
 * else through `FormSchemaRenderFields` — so a prompt card keeps the position
 * of its own key instead of being hoisted above the rest of the form.
 *
 * @param {string[]} keys - Renderable schema keys, in declaration order.
 * @param {Set<string>} promptKeys - The subset of keys holding a prompt ref.
 * @returns {Array<{prompt: boolean, keys: string[]}>} The ordered segments.
 */
function buildFieldSegments(keys, promptKeys) {
  const segments = [];

  for (const key of keys) {
    const prompt = promptKeys.has(key);
    const current = segments[segments.length - 1];
    if (current && current.prompt === prompt) {
      current.keys.push(key);
    } else {
      segments.push({ prompt, keys: [key] });
    }
  }

  return segments;
}

/**
 * Drop-in alternative to `FormSchema` for schemas that declare prompt fields.
 *
 * The schema is walked in declaration order and split into consecutive runs:
 * prompt-typed properties become same-level prompt cards (selector, template
 * preview, create/edit actions) at the exact position of their key, and every
 * other run is delegated to `FormSchemaRenderFields`, so optimizers, unions,
 * nested component references, relevance rules and autosave behave exactly as
 * they do in `FormSchema`. Any schema therefore gains the richer prompt editor
 * without per-schema code.
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

  const segments = useMemo(
    () => buildFieldSegments(orderedKeys, new Set(promptKeys)),
    [orderedKeys, promptKeys],
  );

  // The same relevance pass `FormSchemaRenderFields` runs for every other
  // field: a prompt card has to honour "hide"/"omit" and "disable" too, or a
  // rule that hides a prompt would only apply to whatever renders it next.
  const relevance = useMemo(
    () =>
      evaluateRules(getSchemaRules(modelSchema), formik?.values ?? {})
        .relevance,
    [modelSchema, formik?.values],
  );

  /**
   * Store a prompt field value and let the form report the change.
   *
   * @param {string} key - The prompt field name.
   * @param {object} value - The canonical `{component, params}` reference.
   */
  const handlePromptChange = useCallback(
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
    const fieldState = relevance[key];
    const isIrrelevant = fieldState !== undefined && !fieldState.relevant;
    // "hide" and "omit" both mean "do not render"; "disable" keeps the card
    // visible but inert and explains the rule underneath it.
    if (isIrrelevant && fieldState.effect !== "disable") return null;
    const disabled = isIrrelevant && fieldState.effect === "disable";

    const fieldSchema = modelSchema[key];
    const description =
      disabled && fieldState.reason
        ? `${fieldSchema.description ?? ""}\n\n_${fieldState.reason}_`
        : fieldSchema.description;

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
          onChange: (value) => handlePromptChange(key, value),
        }}
        promptFilter={promptFilter}
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
          {segments.map((segment) =>
            segment.prompt ? (
              segment.keys.map((key) => renderPromptCard(key))
            ) : (
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
            ),
          )}
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
