import { useState } from "react";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelector from "../ColumnSelector";
import { useTourContext } from "../../tour/TourProvider";

export default function ScopeStepExplorer({
  notebook,
  tool,
  setScopeColumns,
  nextStep,
}) {
  const theme = useTheme();
  const [isSelectionValid, setIsSelectionValid] = useState(false);
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = tool?.metadata?.restricted_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};
  const tourContext = useTourContext();

  const handleSubmit = () => {
    nextStep();
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        height: "100%",
        gap: 1,
      }}
      data-tour="column-selector-explorer-container"
    >
      {/* Content */}
      <Box sx={{ flexGrow: 1, overflowY: "auto" }}>
        <Typography variant="subtitle2" gutterBottom>
          Step 1: Select Scope
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: theme.palette.text.secondary, mb: 1 }}
        >
          Select the columns to be used by the explorer.
        </Typography>

        <ColumnSelector
          file_path={notebook.file_path}
          inputCardinality={inputCardinality}
          allowedDtypes={allowedDtypes}
          restrictedDtypes={restrictedDtypes}
          onSelectionChange={(selected) => setScopeColumns(selected)}
          onValidationChange={(isValid) => setIsSelectionValid(isValid)}
        />
      </Box>

      {/* Buttons */}
      <Box
        sx={{
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "flex-end",
          gap: 1,
        }}
      >
        <FormSchemaButtonGroup
          onFormSubmit={handleSubmit}
          error={!isSelectionValid}
          saveButtonText={
            Object.values(tool.schema.properties).length > 0 ? "Next" : "Save"
          }
          data-tour="explorer-scope-next-button"
        />
      </Box>
    </Box>
  );
}
