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
import { columnFieldParam } from "./columnFields";

/** Menu value of the "None" option in a multiple column selector. */
const NONE = "__none__";

/**
 * Right panel of the export metadata step: the platform's export form.
 *
 * The schema fields the exporter marks as column fields are drawn as
 * selectors over the dataset columns the platform can store, so no column
 * name is typed by hand; every other field comes from the exporter's schema
 * through the shared FormSchema. A column picked in a single column field is
 * not offered in the multiple ones, so one column cannot play two roles.
 *
 * @param {string} exporterName - Registered DatasetExporter class name.
 * @param {Array<object>} columnFields - Column fields from ``getColumnFields``.
 * @param {Array<string>} columns - Dataset columns the platform can store.
 * @param {object} columnValues - Picked value of each column field.
 * @param {function} onColumnChange - Called with a field key and its value.
 * @param {object} initialValues - Initial values for the schema form.
 * @param {object} formSubmitRef - Receives the form's formik object.
 * @param {function} onValuesChange - Called with the schema form values.
 * @param {function} setError - Called with whether the schema form has errors.
 */
export default function ExportMetadataPanel({
  exporterName,
  columnFields,
  columns,
  columnValues,
  onColumnChange,
  initialValues,
  formSubmitRef,
  onValuesChange,
  setError,
}) {
  const { t } = useTranslation(["export"]);
  const theme = useTheme();

  const singlePicks = useMemo(
    () =>
      columnFields
        .filter((field) => !field.multiple)
        .map((field) => columnValues[field.key])
        .filter(Boolean),
    [columnFields, columnValues],
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
    if (
      !formik?.setFieldValue ||
      !columnFields.length ||
      !columnFields.every((field) => field.key in (formik.values ?? {}))
    ) {
      return;
    }
    columnFields.forEach((field) => {
      const next = columnFieldParam(field, columnValues[field.key]);
      if (
        JSON.stringify(formik.values[field.key] ?? null) !==
        JSON.stringify(next ?? null)
      ) {
        formik.setFieldValue(field.key, next);
      }
    });
  });

  const handleSingleChange = (field, column) => {
    onColumnChange(field.key, column);
    // A column now used here leaves any multiple field that held it.
    columnFields
      .filter((other) => other.multiple)
      .forEach((other) => {
        const current = columnValues[other.key] ?? [];
        if (current.includes(column)) {
          onColumnChange(
            other.key,
            current.filter((value) => value !== column),
          );
        }
      });
  };

  // An explicit "None" shows at a glance that a field is empty and lets the
  // user empty it again after picking something.
  const noneLabel = (
    <Typography component="span" variant="body2" color="text.secondary">
      {t("export:noColumn")}
    </Typography>
  );

  const renderSelect = (field) => {
    if (!field.multiple) {
      return (
        <Select
          size="small"
          fullWidth
          displayEmpty
          value={columnValues[field.key] ?? ""}
          onChange={(event) => handleSingleChange(field, event.target.value)}
          renderValue={(selected) => selected || noneLabel}
          inputProps={{ "aria-label": field.title }}
        >
          <MenuItem value="">{noneLabel}</MenuItem>
          {columns.map((column) => (
            <MenuItem key={column} value={column}>
              {column}
            </MenuItem>
          ))}
        </Select>
      );
    }
    const options = columns.filter((column) => !singlePicks.includes(column));
    return (
      <Select
        size="small"
        fullWidth
        multiple
        displayEmpty
        value={columnValues[field.key] ?? []}
        onChange={(event) => {
          const picked = event.target.value;
          onColumnChange(field.key, picked.includes(NONE) ? [] : picked);
        }}
        inputProps={{ "aria-label": field.title }}
        renderValue={(selected) =>
          selected.length ? (
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5 }}>
              {selected.map((column) => (
                <Chip key={column} label={column} size="small" />
              ))}
            </Box>
          ) : (
            noneLabel
          )
        }
      >
        <MenuItem value={NONE}>{noneLabel}</MenuItem>
        {options.map((column) => (
          <MenuItem key={column} value={column}>
            {column}
          </MenuItem>
        ))}
      </Select>
    );
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
        {columnFields.map((field) => (
          <Box key={field.key} sx={{ pb: 2 }}>
            <FormSchemaFieldCard
              label={field.title}
              description={field.description}
            >
              {renderSelect(field)}
            </FormSchemaFieldCard>
          </Box>
        ))}

        <FormSchemaContainer>
          <FormSchema
            autoSave
            hideButtons
            model={exporterName}
            initialValues={initialValues}
            formSubmitRef={formSubmitRef}
            setError={setError}
            onValuesChange={handleFormValuesChange}
            excludeFields={columnFields.map((field) => field.key)}
            showBorder={false}
          />
        </FormSchemaContainer>
      </Box>
    </SideBar>
  );
}

ExportMetadataPanel.propTypes = {
  exporterName: PropTypes.string.isRequired,
  columnFields: PropTypes.arrayOf(
    PropTypes.shape({
      key: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      description: PropTypes.string,
      multiple: PropTypes.bool.isRequired,
      required: PropTypes.bool.isRequired,
    }),
  ).isRequired,
  columns: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnValues: PropTypes.object.isRequired,
  onColumnChange: PropTypes.func.isRequired,
  initialValues: PropTypes.object,
  formSubmitRef: PropTypes.shape({ current: PropTypes.any }).isRequired,
  onValuesChange: PropTypes.func.isRequired,
  setError: PropTypes.func.isRequired,
};
