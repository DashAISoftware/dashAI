import { useCallback, useEffect, useMemo } from "react";
import {
  Box,
  Chip,
  MenuItem,
  Select,
  Typography,
  useTheme,
} from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";
import SideBar from "../threeSectionLayout/panelContainers/SideBar";
import FormSchema from "../shared/FormSchema";
import FormSchemaContainer from "../shared/FormSchemaContainer";
import FormSchemaFieldCard from "../shared/FormSchemaFieldCard";

/**
 * Schema fields that name dataset columns. The schema types them as plain
 * strings, so the generic form would show free text boxes; they are drawn
 * here as selectors over the real columns instead, to avoid typos.
 */
export const TARGET_FIELD = "default_target_attribute";
export const IGNORED_FIELD = "ignore_attribute";

/**
 * Right panel of the export metadata step: the platform's export form.
 *
 * The target and ignored columns are selectors over the dataset columns the
 * platform can store; every other field comes from the exporter's schema
 * through the shared FormSchema.
 *
 * @param {string} exporterName - Registered DatasetExporter class name.
 * @param {Array<string>} columns - Dataset columns the platform can store.
 * @param {string} target - Selected target column ("" when none).
 * @param {Array<string>} ignored - Selected ignored columns.
 * @param {function} onTargetChange - Called with the new target column.
 * @param {function} onIgnoredChange - Called with the new ignored columns.
 * @param {object} initialValues - Initial values for the schema form.
 * @param {object} formSubmitRef - Receives the form's formik object.
 * @param {function} onValuesChange - Called with the schema form values.
 * @param {function} setError - Called with whether the schema form has errors.
 */
export default function ExportMetadataPanel({
  exporterName,
  columns,
  target,
  ignored,
  onTargetChange,
  onIgnoredChange,
  initialValues,
  formSubmitRef,
  onValuesChange,
  setError,
}) {
  const { t } = useTranslation(["export"]);
  const theme = useTheme();

  const ignorableColumns = useMemo(
    () => columns.filter((column) => column !== target),
    [columns, target],
  );

  const handleFormValuesChange = useCallback(() => {
    onValuesChange(formSubmitRef?.current?.values || {});
  }, [formSubmitRef, onValuesChange]);

  // The column fields are hidden from the generic form but still part of its
  // values and validation, so the selectors are mirrored into it: the form
  // stays the single source of the values sent and of their errors.
  useEffect(() => {
    const formik = formSubmitRef?.current;
    // Until the schema loads, the form has neither its fields nor its
    // validation, and setting a value would validate against nothing.
    if (!formik?.setFieldValue || !(TARGET_FIELD in (formik.values ?? {}))) {
      return;
    }
    if (formik.values?.[TARGET_FIELD] !== target) {
      formik.setFieldValue(TARGET_FIELD, target);
    }
    const nextIgnored = ignored.length ? ignored : null;
    if (
      JSON.stringify(formik.values?.[IGNORED_FIELD] ?? null) !==
      JSON.stringify(nextIgnored)
    ) {
      formik.setFieldValue(IGNORED_FIELD, nextIgnored);
    }
  });

  const handleTargetChange = (event) => {
    const next = event.target.value;
    onTargetChange(next);
    if (ignored.includes(next)) {
      onIgnoredChange(ignored.filter((column) => column !== next));
    }
  };

  // Same layout as the hub's dataloader panel: a fixed header, then one
  // scroll area where the column cards and the schema form read as a single
  // form (the cards reuse FormSchemaFieldCard, the form's own field shell).
  return (
    <SideBar>
      <Box
        sx={{
          p: 4,
          borderBottom: `1px solid ${theme.palette.ui.border}`,
          flexShrink: 0,
          height: 64,
          display: "flex",
          alignItems: "center",
        }}
      >
        <Typography variant="h6" color="text.primary">
          {t("export:metadataPanelTitle")}
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflowY: "auto", px: 4, pt: 2, pb: 4 }}>
        <Box sx={{ pb: 2 }}>
          <FormSchemaFieldCard
            label={t("export:targetColumn")}
            description={t("export:targetColumnHelp")}
          >
            <Select
              size="small"
              fullWidth
              displayEmpty
              value={target}
              onChange={handleTargetChange}
              inputProps={{ "aria-label": t("export:targetColumn") }}
            >
              {columns.map((column) => (
                <MenuItem key={column} value={column}>
                  {column}
                </MenuItem>
              ))}
            </Select>
          </FormSchemaFieldCard>
        </Box>

        <Box sx={{ pb: 2 }}>
          <FormSchemaFieldCard
            label={t("export:ignoredColumns")}
            description={t("export:ignoredColumnsHelp")}
          >
            <Select
              size="small"
              fullWidth
              multiple
              value={ignored}
              onChange={(event) => onIgnoredChange(event.target.value)}
              inputProps={{ "aria-label": t("export:ignoredColumns") }}
              renderValue={(selected) => (
                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
                  {selected.map((column) => (
                    <Chip key={column} label={column} size="small" />
                  ))}
                </Box>
              )}
            >
              {ignorableColumns.map((column) => (
                <MenuItem key={column} value={column}>
                  {column}
                </MenuItem>
              ))}
            </Select>
          </FormSchemaFieldCard>
        </Box>

        <FormSchemaContainer>
          <FormSchema
            autoSave
            hideButtons
            model={exporterName}
            initialValues={initialValues}
            formSubmitRef={formSubmitRef}
            setError={setError}
            onValuesChange={handleFormValuesChange}
            excludeFields={[TARGET_FIELD, IGNORED_FIELD]}
            showBorder={false}
          />
        </FormSchemaContainer>
      </Box>
    </SideBar>
  );
}

ExportMetadataPanel.propTypes = {
  exporterName: PropTypes.string.isRequired,
  columns: PropTypes.arrayOf(PropTypes.string).isRequired,
  target: PropTypes.string.isRequired,
  ignored: PropTypes.arrayOf(PropTypes.string).isRequired,
  onTargetChange: PropTypes.func.isRequired,
  onIgnoredChange: PropTypes.func.isRequired,
  initialValues: PropTypes.object,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }).isRequired,
  onValuesChange: PropTypes.func.isRequired,
  setError: PropTypes.func.isRequired,
};
