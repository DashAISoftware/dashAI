import { useState } from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaButtonGroup from "../../shared/FormSchemaButtonGroup";
import ColumnSelectionTable from "../../threeSectionLayout/ColumnSelectionTable";

export default function ScopeStepExplorer({
  notebook,
  tool,
  setScopeColumns,
  setStep,
}) {
  const [isSelectionValid, setIsSelectionValid] = useState(false);
  const allowedDtypes = tool?.metadata?.allowed_dtypes || [];
  const restrictedDtypes = tool?.metadata?.restricted_dtypes || [];
  const inputCardinality = tool?.metadata?.input_cardinality || {};

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        flexGrow: 1,
        height: "100%",
        gap: 1,
      }}
    >
      {/* Content */}
      <Box sx={{ flexGrow: 1, overflowY: "auto" }}>
        <Typography variant="subtitle2" gutterBottom>
          Step 1: Select Scope
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          Select the columns to be used by the explorer.
        </Typography>

        <ColumnSelectionTable
          file_path={notebook.file_path}
          inputCardinality={inputCardinality}
          allowedDtypes={allowedDtypes}
          restrictedDtypes={restrictedDtypes}
          onSelectionChange={(selected) => setScopeColumns(selected)}
          onValidationChange={setIsSelectionValid}
          title=""
          description=""
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
          onFormSubmit={() => setStep((s) => s + 1)}
          error={!isSelectionValid}
          saveButtonText="Next"
        />
      </Box>
    </Box>
  );
}
