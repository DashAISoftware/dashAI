import { useMemo, useState } from "react";
import PropTypes from "prop-types";
import { Box, IconButton, Tooltip, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import HelpIcon from "@mui/icons-material/Help";
import ColumnSelector from "../../notebooks/ColumnSelector";
import ConverterTargetColumnModal from "../../notebooks/converterCreation/ConverterTargetColumnModal";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import { getCurrentDataFilePath } from "../../../utils/sessionPreprocessing";

/**
 * Scope step for a session converter: column selection only. Unlike the
 * notebook flow's ScopeStepConverter, there's no row-level scope (the
 * train/test split doesn't exist yet at config time). The target-column ask
 * is back, though: at this point in the wizard the session has no
 * session-wide output/target column yet (that's only fixed once a model is
 * configured), so a SUPERVISED converter (e.g. a feature selector) still
 * needs its own target column picked here, same as the notebook flow.
 */
export default function ScopeStepSessionConverter({
  tool,
  inputColumnNames,
  columnTypes,
  columns,
  setColumns,
  targetColumn,
  setTargetColumn,
  session,
  nextStep,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["common", "datasets", "models"]);
  const [isColumnSelectionValid, setIsColumnSelectionValid] = useState(false);

  const supervised = Boolean(tool?.metadata?.supervised);
  const allowedTypes = tool?.metadata?.allowed_types || [];
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const nonAllowedDtypes = tool?.metadata?.non_allowed_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};
  const excludedColumnIds = useMemo(
    () => (targetColumn ? [targetColumn.idx - 1] : []),
    [targetColumn],
  );

  // Every current column is eligible scope here — output columns aren't
  // chosen yet at this point in the wizard (that's a later step), so
  // there's no "input vs output" distinction to filter by.
  const inputColumnTypes = columnTypes || {};

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
          excludedColumnIds={excludedColumnIds}
          inputCardinality={inputCardinality}
          columnTypes={inputColumnTypes}
          onSelectionChange={setColumns}
          onValidationChange={setIsColumnSelectionValid}
        />
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        {supervised && (
          <ConverterTargetColumnModal
            updateClassColumn={(column) => {
              setTargetColumn({
                idx: column.id + 1,
                columnName: column.columnName,
                valueType: column.valueType,
                dataType: column.dataType,
              });
            }}
            classColumnInitialValue={targetColumn?.idx}
            notebook={{ file_path: getCurrentDataFilePath(session) }}
          />
        )}
        {supervised && (
          <Tooltip
            title={t("datasets:label.helpSelectClassColumn")}
            placement="top"
          >
            <IconButton>
              <HelpIcon />
            </IconButton>
          </Tooltip>
        )}
        <Box sx={{ flexGrow: 1 }}>
          <FormSchemaButtonGroup
            onFormSubmit={nextStep}
            error={!isColumnSelectionValid || (supervised && !targetColumn)}
            saveButtonText={
              hasParams ? t("common:next") : t("models:button.addConverter")
            }
            sx={{ borderTop: 0, pt: 0, mt: 0 }}
          />
        </Box>
      </Box>
    </Box>
  );
}

ScopeStepSessionConverter.propTypes = {
  tool: PropTypes.object.isRequired,
  inputColumnNames: PropTypes.arrayOf(PropTypes.string).isRequired,
  columnTypes: PropTypes.object,
  columns: PropTypes.array.isRequired,
  setColumns: PropTypes.func.isRequired,
  targetColumn: PropTypes.shape({
    idx: PropTypes.number,
    columnName: PropTypes.string,
    valueType: PropTypes.string,
    dataType: PropTypes.string,
  }),
  setTargetColumn: PropTypes.func.isRequired,
  session: PropTypes.object.isRequired,
  nextStep: PropTypes.func.isRequired,
};
