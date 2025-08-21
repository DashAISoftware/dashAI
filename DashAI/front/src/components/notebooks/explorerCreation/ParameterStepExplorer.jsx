import React from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";

export default function ParameterStepExplorer({
  explorer,
  initialParams,
  handleSaveExplorer,
  setStep,
}) {
  return (
    <Box flex={1}>
      <Typography variant="subtitle2" gutterBottom>
        Step 2: Configure Parameters
      </Typography>
      <FormSchemaContainer>
        <FormSchemaWithSelectedModel
          onFormSubmit={handleSaveExplorer}
          modelToConfigure={explorer}
          initialValues={initialParams}
          onCancel={() => setStep(0)}
          saveButtonText="SAVE AND RUN"
        />
      </FormSchemaContainer>
    </Box>
  );
}
