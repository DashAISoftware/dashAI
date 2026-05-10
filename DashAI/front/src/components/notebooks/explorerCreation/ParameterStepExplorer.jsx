import React, { useEffect } from "react";
import { Box, Typography } from "@mui/material";
import FormSchemaWithSelectedModel from "../../shared/FormSchemaWithSelectedModel";
import FormSchemaContainer from "../../shared/FormSchemaContainer";
import { useTourContext } from "../../tour/TourProvider";
import { useTranslation } from "react-i18next";

export default function ParameterStepExplorer({
  explorer,
  initialParams,
  handleSaveExplorer,
  setStep,
}) {
  const tourContext = useTourContext();
  const { t } = useTranslation(["datasets"]);

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
      // Advance tour once this component is mounted and visible
      const timeout = setTimeout(() => {
        tourContext.nextStep();
        const button = document.querySelector(
          '[data-tour="create-explorer-button"]',
        );
        if (button) {
          button.scrollIntoView({
            behavior: "smooth",
            block: "center",
            inline: "nearest",
          });
        }
      }, 300);

      return () => clearTimeout(timeout);
    }
  }, []);

  return (
    <Box flex={1} data-tour="explorer-parameters">
      <Typography
        variant="h6"
        sx={{ fontWeight: 700, color: "primary.main", mb: 2 }}
      >
        {t("datasets:label.configureParameters")}
      </Typography>
      <FormSchemaContainer>
        <FormSchemaWithSelectedModel
          onFormSubmit={handleSave}
          modelToConfigure={explorer}
          initialValues={initialParams}
          onCancel={() => setStep(0)}
          saveButtonText={t("datasets:button.createExplorer")}
        />
      </FormSchemaContainer>
    </Box>
  );
}
