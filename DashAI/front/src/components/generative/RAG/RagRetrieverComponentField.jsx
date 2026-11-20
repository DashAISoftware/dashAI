import { useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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

/**
 * Registry parents whose components this field renders: every retriever and
 * every chunk scorer, composite or not.
 */
export const RETRIEVER_FIELD_PARENTS = ["BaseRetriever", "ChunkScorer"];

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
    fieldSchema.type === "object" &&
    RETRIEVER_FIELD_PARENTS.includes(fieldSchema.parent) &&
    fieldSchema.placeholder?.optimize === undefined
  ) {
    return { parent: fieldSchema.parent, nullable: false };
  }
  if (Array.isArray(fieldSchema.anyOf)) {
    const objectBranch = fieldSchema.anyOf.find(
      (branch) =>
        branch?.type === "object" &&
        RETRIEVER_FIELD_PARENTS.includes(branch.parent),
    );
    const accepted = fieldSchema.anyOf.filter(
      (branch) => branch?.type === "object" || branch?.type === "null",
    );
    // Any other branch (a number, a string) means this is a general union and
    // belongs to the generic renderer.
    if (objectBranch && accepted.length === fieldSchema.anyOf.length) {
      return {
        parent: objectBranch.parent,
        nullable: fieldSchema.anyOf.some((branch) => branch?.type === "null"),
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
 * field. When `nullable`, a Component/Null switch turns the field off.
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
  const { models } = useModelParents({ parent });
  const [openDialog, setOpenDialog] = useState(false);
  const formikRef = useRef(null);

  const isNull = field?.value === null || field?.value === undefined;
  const selectedName = isNull ? null : getModelFromSubform(field.value);
  const selected = models?.find((model) => model.name === selectedName);
  const containerField = findChildrenField(selected?.schema);

  const { defaultValues: defaultParams } = useSchema({
    modelName: selectedName,
  });

  // Only a composite can be incomplete; the tree reports its own verdict, and
  // anything else (no selection, a plain component, Null) is complete.
  useEffect(() => {
    if (!containerField) onValidityChange?.(true);
  }, [containerField, onValidityChange]);

  // A field that unmounts (a rule hides it) must not keep Done disabled.
  useEffect(() => () => onValidityChange?.(true), [onValidityChange]);

  const currentParams = () =>
    getParamsFromSubform(field?.value) ?? defaultParams ?? {};

  const writeValue = (modelName, params) =>
    field.onChange(formattedSubform({ parent, model: modelName, params }));

  const handleSelect = async (event) => {
    const model = models?.find((item) => item.name === event.target.value);
    if (!model?.schema) return;
    const { initialValues } = generateYupSchema(
      await formattedModel(model.schema),
    );
    writeValue(model.name, initialValues);
  };

  const handleTypeChange = (type) => {
    field.onChange(type === "null" ? null : placeholder);
  };

  const handleDialogSave = () => {
    writeValue(selectedName, formikRef.current?.values ?? currentParams());
    setOpenDialog(false);
  };

  const typeSelector = nullable ? (
    <SingleSelectChipGroup
      options={[
        { key: "object", label: t("common:component", "Component") },
        { key: "null", label: "Null" },
      ]}
      selected={isNull ? "null" : "object"}
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
            disabled={disabled}
            onClick={() => setOpenDialog(true)}
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
        errorMessage={errorMessage}
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
            {models?.map((model) => (
              <MenuItem key={model.name} value={model.name}>
                {model.display_name || model.name}
              </MenuItem>
            ))}
          </Input>
        )}
        {!isNull && selectedName && containerField && (
          <Box sx={{ mt: 2 }}>
            <CompositeRetrieverBuilder
              key={`tree-${selectedName}`}
              rootComponent={selectedName}
              rootParams={currentParams()}
              onChange={(tree) => writeValue(tree.component, tree.params)}
              onValidityChange={onValidityChange}
            />
          </Box>
        )}
      </FormSchemaFieldCard>

      <Dialog
        open={openDialog}
        onClose={() => setOpenDialog(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { maxHeight: "80vh", zIndex: 1400 } }}
        BackdropProps={{ sx: { zIndex: 1399 } }}
      >
        <DialogTitle>{`${selectedName} Configuration`}</DialogTitle>
        <DialogContent dividers sx={{ minHeight: 200 }}>
          {selectedName && !containerField && (
            <FormSchemaContainer key={`retriever-form-${selectedName}`}>
              <FormSchema
                model={selectedName}
                initialValues={currentParams()}
                onFormSubmit={(values) => writeValue(selectedName, values)}
                autoSave={false}
                formSubmitRef={formikRef}
                hideButtons
              />
            </FormSchemaContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)} color="inherit">
            {t("common:cancel")}
          </Button>
          <Button onClick={handleDialogSave} variant="contained">
            {t("common:save")}
          </Button>
        </DialogActions>
      </Dialog>
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
