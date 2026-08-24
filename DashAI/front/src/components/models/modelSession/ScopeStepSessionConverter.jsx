import { useState } from "react";
import PropTypes from "prop-types";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import ColumnSelector from "../../notebooks/ColumnSelector";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";

/**
 * Scope step for a session converter: column selection only. Unlike the
 * notebook flow's ScopeStepConverter, there's no row-level scope (the
 * train/test split doesn't exist yet at config time) and no target-column
 * ask (the session's output column is already fixed).
 */
export default function ScopeStepSessionConverter({
  tool,
  inputColumnNames,
  columnTypes,
  columns,
  setColumns,
  nextStep,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["common", "datasets", "models"]);
  const [isColumnSelectionValid, setIsColumnSelectionValid] = useState(false);

  const allowedTypes = tool?.metadata?.allowed_types || [];
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const nonAllowedDtypes = tool?.metadata?.non_allowed_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};

  // Only input columns can be transformed by a session converter — the
  // output column is never part of X.
  const inputColumnTypes = Object.fromEntries(
    Object.entries(columnTypes || {}).filter(([name]) =>
      inputColumnNames.includes(name),
    ),
  );

  const hasParams = Object.values(tool.schema.properties).length > 0;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        height: "100%",
        gap: 2,
        minHeight: 0,
      }}
    >
      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.primary, mb: 1 }}
        >
          {t("datasets:label.selectScopeDescriptionColumns")}
        </Typography>
        <ColumnSelector
          file_path=""
          tool={tool}
          allowedTypes={allowedTypes}
          allowedDtypes={allowedDtypes}
          nonAllowedDtypes={nonAllowedDtypes}
          inputCardinality={inputCardinality}
          columnTypes={inputColumnTypes}
          onSelectionChange={setColumns}
          onValidationChange={setIsColumnSelectionValid}
        />
      </Box>
      <FormSchemaButtonGroup
        onFormSubmit={nextStep}
        error={!isColumnSelectionValid}
        saveButtonText={
          hasParams ? t("common:next") : t("models:button.addConverter")
        }
        sx={{ borderTop: 0, pt: 0, mt: 0 }}
      />
    </Box>
  );
}

ScopeStepSessionConverter.propTypes = {
  tool: PropTypes.object.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  columns: PropTypes.array.isRequired,
  setColumns: PropTypes.func.isRequired,
  nextStep: PropTypes.func.isRequired,
};
