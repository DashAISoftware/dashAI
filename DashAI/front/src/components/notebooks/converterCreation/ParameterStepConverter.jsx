import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { useTourContext } from "../../tour/TourProvider";

export default function ParameterStepConverter({
  converter,
  initialParams,
  handleSaveConverter,
  setStep,
}) {
  const tourContext = useTourContext();

  const handleSave = async (params) => {
    await handleSaveConverter(params);

    if (tourContext && tourContext.run) {
      setTimeout(() => {
        tourContext.nextStep();
      }, 500);
    }
  };

  useEffect(() => {
    if (tourContext?.run) {
      const timeout = setTimeout(() => {
        const button = document.querySelector(
          '[data-tour="create-converter-button"]',
        );
        if (button) {
          const dialogContent = button.closest(".MuiDialogContent-root");
          if (dialogContent) {
            const rect = button.getBoundingClientRect();
            const containerRect = dialogContent.getBoundingClientRect();
            const relativeTop = rect.top - containerRect.top;
            const scrollTop =
              dialogContent.scrollTop +
              relativeTop -
              dialogContent.clientHeight / 2 +
              rect.height / 2;

            dialogContent.scrollTo({
              top: Math.max(0, scrollTop),
              behavior: "smooth",
            });
          }
        }
      }, 500);

      return () => clearTimeout(timeout);
    }
  }, [tourContext?.stepIndex, tourContext?.run]);

  return (
    <Box flex={1} data-tour="converter-parameters">
      <Typography variant="subtitle2" gutterBottom>
        Step 2: Configure Parameters
      </Typography>
      <FormSchemaContainer>
        <FormSchemaWithSelectedModel
          onFormSubmit={handleSave}
          modelToConfigure={converter}
          initialValues={initialParams}
          onCancel={() => setStep(0)}
          saveButtonText="Create Converter"
        />
      </FormSchemaContainer>
    </Box>
  );
}
