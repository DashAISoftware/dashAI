import { useState } from "react";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelector from "../ColumnSelector";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

export default function ScopeStepExplorer({
  notebook,
  tool,
  setScopeColumns,
  nextStep,
  hideButtons = false,
}) {
  const theme = useTheme();
  const [isSelectionValid, setIsSelectionValid] = useState(false);
  const allowedTypes = tool?.metadata?.allowed_types || [];
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets", "common"]);

  const handleSubmit = () => {
    nextStep();
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flex: 1,
        height: "100%",
        minHeight: 0,
      }}
      data-tour="column-selector-explorer-container"
    >
      {/* Content */}
      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        <Typography
          variant="h6"
          sx={{ fontWeight: 700, color: theme.palette.primary.main, mb: 0.5 }}
        >
          {t("datasets:label.selectScopeStep", {
            step: 1,
          })}
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.primary, mb: 1.5 }}
        >
          {t("datasets:label.selectColumnsForExplorerScope")}
        </Typography>

        <ColumnSelector
          file_path={notebook.file_path}
          inputCardinality={inputCardinality}
          allowedTypes={allowedTypes}
          allowedDtypes={allowedDtypes}
          onSelectionChange={(selected) => setScopeColumns(selected)}
          onValidationChange={(isValid) => setIsSelectionValid(isValid)}
        />
      </Box>

      {/* Buttons */}
      {!hideButtons && (
        <FormSchemaButtonGroup
          onFormSubmit={handleSubmit}
          error={!isSelectionValid}
          saveButtonText={
            Object.values(tool.schema.properties).length > 0
              ? t("common:next")
              : t("common:save")
          }
          data-tour="explorer-scope-next-button"
        />
      )}
    </Box>
  );
}
