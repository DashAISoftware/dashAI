import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  IconButton,
  MenuItem,
  Tooltip,
} from "@mui/material";
import { Settings } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { Input } from "../../configurableObject/Inputs/InputStyles";
import FormSchemaFieldCard from "../../shared/FormSchemaFieldCard";
import FormSchema from "../../shared/FormSchema";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import SingleSelectChipGroup from "../../shared/SingleSelectChipGroup";
import { findChildrenField } from "../../shared/componentTree/componentTreeUtils";
import useModelParents from "../../../hooks/useModelParents";
import useSchema from "../../../hooks/useSchema";
import {
  formattedModel,
  formattedSubform,
  generateYupSchema,
  getModelFromSubform,
  getParamsFromSubform,
} from "../../../utils/schema";
import CompositeRetrieverBuilder from "../../../pages/generative/RAGSession/advanced/CompositeRetrieverBuilder";
import RAGAdvancedDialog from "../../shared/RAGAdvancedDialog";
import {
  OPTIMIZE_PLACEHOLDER_KEY,
  SCHEMA_TYPE_NULL,
  SCHEMA_TYPE_OBJECT,
} from "../../../constants/rag";
import { RETRIEVER_FIELD_PARENTS } from "./retrieverParents";

export { RETRIEVER_FIELD_PARENTS };

/** The two states of a nullable retriever field, as the chip group's keys. */
const FIELD_MODE_COMPONENT = "component";
const FIELD_MODE_NULL = "null";

/** The z-index that stacks the settings dialog above the dialog that holds the form. */
const SETTINGS_DIALOG_Z_INDEX = 1400;

/**
 * Whether a schema property is a retriever component reference, optional or
 * not.
 *
 * Matches a component field whose declared parent is a retriever family, in
 * its plain form and in the nullable form (`anyOf` of that object and null),
 * so the reranker of a transformation stage and any similar field get this
 * field without per-schema code.
 *
 * @param {object} fieldSchema - The property schema to inspect.
 * @returns {{parent: string, nullable: boolean}|null} The declared parent and
 *   whether null is accepted, or null when it is not a retriever field.
 */
export function retrieverFieldInfo(fieldSchema) {
  if (!fieldSchema) return null;
  if (
    fieldSchema.type === SCHEMA_TYPE_OBJECT &&
    RETRIEVER_FIELD_PARENTS.includes(fieldSchema.parent) &&
    fieldSchema.placeholder?.[OPTIMIZE_PLACEHOLDER_KEY] === undefined
  ) {
    return { parent: fieldSchema.parent, nullable: false };
  }
  if (Array.isArray(fieldSchema.anyOf)) {
    const objectBranch = fieldSchema.anyOf.find(
      (branch) =>
        branch?.type === SCHEMA_TYPE_OBJECT &&
        RETRIEVER_FIELD_PARENTS.includes(branch.parent),
    );
    const accepted = fieldSchema.anyOf.filter(
      (branch) =>
        branch?.type === SCHEMA_TYPE_OBJECT ||
        branch?.type === SCHEMA_TYPE_NULL,
    );
    if (objectBranch && accepted.length === fieldSchema.anyOf.length) {
      return {
        parent: objectBranch.parent,
        nullable: fieldSchema.anyOf.some(
          (branch) => branch?.type === SCHEMA_TYPE_NULL,
        ),
      };
    }
  }
  return null;
}

/**
 * Retriever selector for RAG forms that keeps the whole configuration visible.
 *
 * A card with the component selector. A composite (a component that declares
 * children) shows its tree right under the selector, so its children are never
 * hidden behind a button, and the field reports through `onValidityChange`
 * whether every composite has its children. A component with no children is
 * configured through the settings button, as in any other nested component
 * field. When `nullable`, a Component/Null switch turns the field off; only an
 * explicit `null` value means off, so an unset value shows the selector with no
 * choice made.
 *
 * @param {object} props
 * @param {string} props.name - Field name, used as the card key.
 * @param {string} props.parent - Registry parent the options inherit from.
 * @param {string} props.label - Card label.
 * @param {object} props.field - `{value, onChange}` of the field.
 * @param {string} [props.description] - Card description.
 * @param {string} [props.errorMessage] - Validation message for the card.
 * @param {boolean} [props.nullable] - Whether null (feature off) is accepted.
 * @param {object} [props.placeholder] - Reference restored when the switch
 *   goes back from Null to Component.
 * @param {boolean} [props.disabled] - Renders the field inert.
 * @param {function(boolean): void} [props.onValidityChange] - Whether the
 *   field's value can be saved: false while a composite lacks children.
 * @returns {JSX.Element} The retriever field.
 */
export default function RagRetrieverComponentField({
  name,
  parent,
  label,
  field,
  description,
  errorMessage,
  nullable = false,
  placeholder,
  disabled = false,
  onValidityChange,
}) {
  const { t } = useTranslation(["common", "generative"]);
  const { models, error: modelsError } = useModelParents({ parent });
  const [openDialog, setOpenDialog] = useState(false);
  const [selectError, setSelectError] = useState(null);
  const [dialogError, setDialogError] = useState(null);
  const formikRef = useRef(null);
  const selectRequestRef = useRef(0);

  const isNull = nullable && field?.value === null;
  const selectedName = field?.value ? getModelFromSubform(field.value) : null;
  const selected = models?.find((model) => model.name === selectedName);
  const containerField = findChildrenField(selected?.schema);
  const modelsPending = Boolean(selectedName) && models === null;

  const { modelSchema, defaultValues: defaultParams } = useSchema({
    modelName: selectedName,
  });

  /**
   * The params the selected component currently holds: the stored ones, or its
   * schema defaults once loaded.
   * @returns {object|null} The params, or null while the defaults load.
   */
  const currentParams = () => {
    const stored = getParamsFromSubform(field?.value);
    if (stored) return stored;
    return modelSchema ? defaultParams : null;
  };

  const rootParams = currentParams();
  const compositeLoading = Boolean(
    selectedName && containerField && rootParams === null,
  );

  useEffect(() => {
    if (modelsPending || compositeLoading) {
      onValidityChange?.(false);
      return;
    }
    if (!containerField) onValidityChange?.(true);
  }, [modelsPending, compositeLoading, containerField, onValidityChange]);

  useEffect(() => () => onValidityChange?.(true), [onValidityChange]);

  useEffect(
    () => () => {
      selectRequestRef.current += 1;
    },
    [],
  );

  /**
   * Stores a component and its params as the field value.
   * @param {string} modelName - The component name.
   * @param {object} params - The component params.
   */
  const writeValue = (modelName, params) =>
    field.onChange(formattedSubform({ parent, model: modelName, params }));

  /**
   * Selects a component and seeds its params from its schema. A selection that
   * a newer one overtook while its schema was loading is dropped.
   * @param {object} event - The select change event.
   */
  const handleSelect = async (event) => {
    const model = models?.find((item) => item.name === event.target.value);
    selectRequestRef.current += 1;
    const requestId = selectRequestRef.current;
    if (!model?.schema) {
      setSelectError(
        t("common:componentTree.noSchema", { component: event.target.value }),
      );
      return;
    }
    try {
      const { initialValues } = generateYupSchema(
        await formattedModel(model.schema),
      );
      if (requestId !== selectRequestRef.current) return;
      setSelectError(null);
      writeValue(model.name, initialValues);
    } catch (error) {
      if (requestId !== selectRequestRef.current) return;
      setSelectError(error?.message ?? String(error));
    }
  };

  /**
   * Switches the field between a component and Null.
   * @param {string} mode - FIELD_MODE_COMPONENT, or FIELD_MODE_NULL to turn it off.
   */
  const handleTypeChange = (mode) => {
    if (mode === FIELD_MODE_NULL) {
      field.onChange(null);
      return;
    }
    field.onChange(placeholder);
  };

  /**
   * Submits the settings form, which stores its values in the field, and closes
   * the dialog only when they are valid. A form that is not mounted yet is
   * reported instead of saving something else.
   */
  const handleDialogSave = async () => {
    const formik = formikRef.current;
    if (formik === null) {
      setDialogError(t("common:componentTree.formUnavailable"));
      return;
    }
    await formik.submitForm();
    const errors = await formik.validateForm();
    if (Object.keys(errors).length > 0) return;
    setDialogError(null);
    setOpenDialog(false);
  };

  const loadErrorReason = selectError ?? modelsError?.message;
  const cardError =
    errorMessage ??
    (loadErrorReason
      ? t("common:componentTree.loadFailed", { reason: loadErrorReason })
      : undefined);
  let modeSelected = FIELD_MODE_COMPONENT;
  if (isNull) modeSelected = FIELD_MODE_NULL;

  const typeSelector = nullable ? (
    <SingleSelectChipGroup
      options={[
        { key: FIELD_MODE_COMPONENT, label: t("common:component") },
        { key: FIELD_MODE_NULL, label: t("common:null") },
      ]}
      selected={modeSelected}
      onChange={handleTypeChange}
      disabled={disabled}
    />
  ) : null;

  const configureButton =
    selectedName && !containerField ? (
      <Tooltip title={t("common:configureSubmodel")}>
        <span>
          <IconButton
            size="small"
            aria-label={t("common:configureSubmodel")}
            disabled={disabled}
            onClick={() => {
              setDialogError(null);
              setOpenDialog(true);
            }}
          >
            <Settings fontSize="small" />
          </IconButton>
        </span>
      </Tooltip>
    ) : null;

  return (
    <>
      <FormSchemaFieldCard
        label={label}
        paramKey={name}
        description={description}
        errorMessage={cardError}
        headerRight={
          typeSelector || configureButton ? (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              {typeSelector}
              {configureButton}
            </Box>
          ) : null
        }
      >
        {!isNull && (
          <Input
            select
            size="small"
            disabled={disabled}
            value={selectedName ?? ""}
            onChange={handleSelect}
            sx={{ width: "100%" }}
          >
            {(models ?? []).map((model) => (
              <MenuItem key={model.name} value={model.name}>
                {model.display_name || model.name}
              </MenuItem>
            ))}
          </Input>
        )}
        {!isNull && selectedName && containerField && rootParams && (
          <Box sx={{ mt: 2 }}>
            <CompositeRetrieverBuilder
              key={`tree-${selectedName}`}
              rootComponent={selectedName}
              rootParams={rootParams}
              rootParent={parent}
              onChange={(tree) => writeValue(tree.component, tree.params)}
              onValidityChange={onValidityChange}
            />
          </Box>
        )}
      </FormSchemaFieldCard>

      <RAGAdvancedDialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        title={t("common:modelToConfig", { model: selectedName })}
        maxWidth="sm"
        minHeight={200}
        dialogProps={{ sx: { zIndex: SETTINGS_DIALOG_Z_INDEX } }}
        actions={
          <>
            <Button onClick={() => setOpenDialog(false)} color="inherit">
              {t("common:cancel")}
            </Button>
            <Button onClick={handleDialogSave} variant="contained">
              {t("common:save")}
            </Button>
          </>
        }
      >
        {dialogError !== null && (
          <Alert severity="error" sx={{ py: 0.5, mb: 1 }}>
            {dialogError}
          </Alert>
        )}
        {selectedName && !containerField && (
          <FormSchemaContainer key={`retriever-form-${selectedName}`}>
            <FormSchema
              model={selectedName}
              initialValues={rootParams ?? defaultParams}
              onFormSubmit={(values) => writeValue(selectedName, values)}
              autoSave={false}
              formSubmitRef={formikRef}
              hideButtons
            />
          </FormSchemaContainer>
        )}
      </RAGAdvancedDialog>
    </>
  );
}

RagRetrieverComponentField.propTypes = {
  name: PropTypes.string.isRequired,
  parent: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  field: PropTypes.shape({
    value: PropTypes.any,
    onChange: PropTypes.func.isRequired,
  }).isRequired,
  description: PropTypes.string,
  errorMessage: PropTypes.string,
  nullable: PropTypes.bool,
  placeholder: PropTypes.object,
  disabled: PropTypes.bool,
  onValidityChange: PropTypes.func,
};
