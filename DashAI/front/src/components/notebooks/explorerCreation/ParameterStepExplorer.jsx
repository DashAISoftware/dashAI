import React, { useEffect, useRef, useState } from "react";
import { Box, Typography, Button } from "@mui/material";
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
  const { t } = useTranslation(["datasets", "common"]);
  const submitRef = useRef(null);
  const [hasError, setHasError] = useState(false);

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
        tourContext.nextStep();
      }, 300);
      return () => clearTimeout(timeout);
    }
  }, []);

  return (
    <Box
      sx={{ display: "flex", flexDirection: "column", flex: 1, height: "100%" }}
      data-tour="explorer-parameters"
    >
      <Box sx={{ flexGrow: 1, overflowY: "auto" }}>
        <Typography
          variant="h6"
          sx={{ fontWeight: 700, color: "primary.main", mb: 1 }}
        >
          {t("datasets:label.configureParametersStep", { step: 2 })}
        </Typography>
        <FormSchemaContainer>
          <FormSchemaWithSelectedModel
            onFormSubmit={handleSave}
            modelToConfigure={explorer}
            initialValues={initialParams}
            onCancel={() => setStep(0)}
            saveButtonText={t("datasets:button.createExplorer")}
            hideButtons={true}
            formSubmitRef={submitRef}
            onErrorChange={setHasError}
          />
        </FormSchemaContainer>
      </Box>

      <Box
        sx={{
          flexShrink: 0,
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
          pt: 1,
        }}
      >
        <Button variant="outlined" onClick={() => setStep(0)}>
          {t("common:back")}
        </Button>
        <Button
          variant="contained"
          onClick={() => submitRef.current?.()}
          disabled={hasError}
          data-tour="create-explorer-button"
        >
          {t("datasets:button.createExplorer")}
        </Button>
      </Box>
    </Box>
  );
}
