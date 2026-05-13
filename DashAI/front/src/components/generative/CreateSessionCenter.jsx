import {
  Box,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import ComponentSelector from "../custom/ComponentSelector";
import GenerativeBreadcrumbs from "./GenerativeBreadcrumbs";
import { useCreateSession } from "./CreateSessionContext";
import StepperNavigationFooter from "../shared/StepperNavigationFooter";
import { useTourContext } from "../tour/TourProvider";

export default function CreateSessionCenter() {
  const { t } = useTranslation(["generative", "common"]);
  const tourContext = useTourContext();

  useEffect(() => {
    if (!tourContext?.run) return;
    const currentTarget = tourContext.steps?.[tourContext.stepIndex]?.target;
    if (currentTarget === '[data-tour="task-gallery"]') {
      tourContext.resumeAtStep(tourContext.stepIndex);
    }
  }, []);

  const {
    step,
    models,
    loadingModels,
    selectedModel,
    handleSelectModel,
    formik,
    submitting,
    handleNext,
    handleBack,
    handleCreate,
  } = useCreateSession();

  const canGoNext = !!selectedModel;
  const canCreate =
    !!selectedModel && !!formik.values.name?.trim() && !submitting;

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        width: "100%",
        minHeight: 0,
        p: 2,
      }}
    >
      <GenerativeBreadcrumbs />
      <Box sx={{ mb: 2 }} data-tour="task-gallery">
        <Typography variant="h5" component="h2">
          {step === 0
            ? t("generative:label.selectModel")
            : t("generative:label.configureSession")}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {step === 0
            ? t("generative:label.pickAModelGroupedByTask")
            : t("generative:label.nameAndDescribeYourSession")}
        </Typography>
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          overflowY: "auto",
          pt: 1,
        }}
      >
        {step === 0 ? (
          loadingModels ? (
            <Box
              sx={{
                flex: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CircularProgress />
            </Box>
          ) : (
            <ComponentSelector
              components={models}
              selected={selectedModel}
              onSelect={handleSelectModel}
              categoryKey="task_display_name"
              searchPlaceholder={t("generative:label.searchModels")}
            />
          )
        ) : (
          <Stack spacing={2} sx={{ maxWidth: "100%" }}>
            <TextField
              fullWidth
              label={t("generative:label.sessionName")}
              name="name"
              value={formik.values.name || ""}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
              error={Boolean(formik.touched.name && formik.errors.name)}
              helperText={formik.touched.name && formik.errors.name}
            />
            <TextField
              fullWidth
              multiline
              minRows={3}
              label={t("generative:label.sessionDescription")}
              name="description"
              value={formik.values.description || ""}
              onChange={formik.handleChange}
              onBlur={formik.handleBlur}
            />
          </Stack>
        )}
      </Box>

      <StepperNavigationFooter
        onBack={handleBack}
        onNext={step === 0 ? handleNext : handleCreate}
        backDisabled={submitting}
        nextDisabled={step === 0 ? !canGoNext : !canCreate}
        nextLabel={
          step === 0 ? t("common:next") : t("generative:button.createSession")
        }
        loading={submitting}
        variant={step === 0 ? "next" : "save"}
      />
    </Box>
  );
}
