import { useState, useEffect, useRef } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Divider,
  TextField,
  Typography,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import FormSchemaContainer from "../FormSchemaContainer";
import RAGAdvancedDialog from "../../../pages/generative/RAGSession/advanced/RAGAdvancedDialog";
import { resolveLocalizedText } from "../../../utils/localize";
import { componentCategory } from "./componentTreeUtils";

/** Shared empty exclusion list, so a plain component passes no new array. */
const NO_EXCLUDED_FIELDS = [];

/**
 * Dialog for configuring one node of the component tree: choose its component
 * from the options it may take and edit its parameters.
 *
 * @param {object} props
 * @param {boolean} props.open - Whether the dialog is open.
 * @param {string} props.nodeId - The target node id.
 * @param {object} [props.nodeData] - The current node (component + params).
 * @param {object[]} props.options - The components the node may take.
 * @param {function(string): ({key: string}|null)} props.getChildrenField -
 *   The children field of a component, or null when it is not a container. The
 *   children are edited in the tree, so their field is left out of the form.
 * @param {function(string): Promise<object>} props.resolveDefaults - Default
 *   form values of a component.
 * @param {React.ElementType} props.FormComponent - Schema form that edits the
 *   params. Receives `model`, `initialValues`, `autoSave`, `onFormSubmit`,
 *   `hideButtons` and `excludeFields`.
 * @param {object} props.labels - Resolved texts (`configureNode`,
 *   `selectComponent`, `parameters`, `containerNote`).
 * @param {function(string, string, object): void} props.onSave - Receives
 *   `(nodeId, component, params)`.
 * @param {function(): void} props.onClose - Closes the dialog.
 * @returns {JSX.Element} The configuration dialog.
 */
export default function ComponentTreeNodeConfig({
  open,
  nodeId,
  nodeData,
  options,
  getChildrenField,
  resolveDefaults,
  FormComponent,
  labels,
  onSave,
  onClose,
}) {
  const { t, i18n } = useTranslation(["common"]);
  const [selected, setSelected] = useState(null);
  const [params, setParams] = useState({});
  const [initialParams, setInitialParams] = useState({});
  const [loadingDefaults, setLoadingDefaults] = useState(false);
  const defaultsRequestRef = useRef(0);

  useEffect(() => {
    if (!nodeData || !options.length) return;
    setSelected(options.find((c) => c.name === nodeData.component) || null);
    const current = nodeData.params;
    setParams(current);
    setInitialParams(current);
  }, [nodeData, options]);

  const childrenField = selected ? getChildrenField(selected.name) : null;

  /**
   * Selects a component and loads its default parameters. Only the latest
   * request may write the form state, so quickly switching components cannot
   * apply a stale response.
   * @param {object} _event - The autocomplete event.
   * @param {object|null} value - The newly selected component.
   */
  const handleChange = async (_event, value) => {
    const requestId = defaultsRequestRef.current + 1;
    defaultsRequestRef.current = requestId;
    setSelected(value);

    if (!value) {
      setParams({});
      setLoadingDefaults(false);
      return;
    }

    setLoadingDefaults(true);
    try {
      const defaults = await resolveDefaults(value.name);
      if (requestId !== defaultsRequestRef.current) return;
      setParams(defaults);
      setInitialParams(defaults);
    } finally {
      if (requestId === defaultsRequestRef.current) setLoadingDefaults(false);
    }
  };

  const actions = (
    <>
      <Button onClick={onClose} variant="outlined">
        {t("common:cancel")}
      </Button>
      <Button
        onClick={() => selected && onSave(nodeId, selected.name, params)}
        variant="contained"
        loading={loadingDefaults}
        disabled={!selected || loadingDefaults}
      >
        {t("common:save")}
      </Button>
    </>
  );

  return (
    <RAGAdvancedDialog
      open={open}
      onClose={onClose}
      title={labels.configureNode}
      maxWidth="sm"
      minHeight={300}
      contentSx={{ maxHeight: "85vh" }}
      actions={actions}
    >
      <Box sx={{ display: "flex", flexDirection: "column", gap: 3, pt: 1 }}>
        <Autocomplete
          options={options}
          value={selected}
          onChange={handleChange}
          getOptionLabel={(option) =>
            resolveLocalizedText(option?.display_name, i18n) ||
            option?.name ||
            ""
          }
          isOptionEqualToValue={(a, b) => a.name === b.name}
          groupBy={(option) => componentCategory(option, t("common:other"))}
          renderInput={(inputParams) => (
            <TextField {...inputParams} label={labels.selectComponent} />
          )}
        />

        {childrenField && (
          <Typography variant="caption" color="text.secondary">
            {labels.containerNote}
          </Typography>
        )}

        {selected && (
          <>
            <Divider />
            <Typography variant="subtitle2">{labels.parameters}</Typography>
            <FormSchemaContainer key={`node-config-${nodeId}-${selected.name}`}>
              <FormComponent
                model={selected.name}
                initialValues={initialParams}
                autoSave
                onFormSubmit={(values) => setParams(values)}
                hideButtons
                excludeFields={
                  childrenField ? [childrenField.key] : NO_EXCLUDED_FIELDS
                }
              />
            </FormSchemaContainer>
          </>
        )}
      </Box>
    </RAGAdvancedDialog>
  );
}

ComponentTreeNodeConfig.propTypes = {
  open: PropTypes.bool.isRequired,
  nodeId: PropTypes.string.isRequired,
  nodeData: PropTypes.object,
  options: PropTypes.array.isRequired,
  getChildrenField: PropTypes.func.isRequired,
  resolveDefaults: PropTypes.func.isRequired,
  FormComponent: PropTypes.elementType.isRequired,
  labels: PropTypes.object.isRequired,
  onSave: PropTypes.func.isRequired,
  onClose: PropTypes.func.isRequired,
};
