import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { useTourContext } from "../../tour/TourProvider";

export default function ParameterStepExplorer({
  explorer,
  initialParams,
  handleSaveExplorer,
  setStep,
}) {
  const tourContext = useTourContext();

  const handleSave = async (params) => {
    await handleSaveExplorer(params);
    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  useEffect(() => {
    if (tourContext?.run) { 
      const timeout = setTimeout(() => {
        const button = document.querySelector('[data-tour="create-explorer-button"]');
        if (button) {
          button.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'center',
            inline: 'nearest'
          });
        }
      }, 300);
      
      return () => clearTimeout(timeout);
    }
  }, [tourContext?.stepIndex, tourContext?.run]);

  return (
    <Box flex={1} data-tour="explorer-parameters">
      <Typography variant="subtitle2" gutterBottom>
        Step 2: Configure Parameters
      </Typography>
      <FormSchemaContainer>
        <FormSchemaWithSelectedModel
          onFormSubmit={handleSave}
          modelToConfigure={explorer}
          initialValues={initialParams}
          onCancel={() => setStep(0)}
          saveButtonText="Create Explorer"
        />
      </FormSchemaContainer>
    </Box>
  );
}