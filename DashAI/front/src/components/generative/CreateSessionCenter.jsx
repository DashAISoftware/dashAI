import {
  Box,
  Button,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import ComponentSelector from "../custom/ComponentSelector";
import GenerativeBreadcrumbs from "./GenerativeBreadcrumbs";
import { useCreateSession } from "./CreateSessionContext";

export default function CreateSessionCenter() {
  const { t } = useTranslation(["generative", "common"]);
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
    handleCancel,
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
        p: 3,
      }}
    >
      <GenerativeBreadcrumbs />
      <Box sx={{ mb: 2 }}>
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
        sx={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}
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

      <Box
        sx={{
          mt: 2,
          pt: 2,
          borderTop: 1,
          borderColor: "divider",
          display: "flex",
          justifyContent: "flex-end",
          gap: 1,
        }}
      >
        {step === 1 && (
          <Button variant="outlined" onClick={handleBack} disabled={submitting}>
            {t("common:back")}
          </Button>
        )}
        <Button variant="text" onClick={handleCancel} disabled={submitting}>
          {t("common:cancel")}
        </Button>
        {step === 0 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={!canGoNext}
          >
            {t("common:next")}
          </Button>
        ) : (
          <Button
            variant="contained"
            onClick={handleCreate}
            disabled={!canCreate}
          >
            {submitting
              ? t("common:saving")
              : t("generative:button.createSession")}
          </Button>
        )}
      </Box>
    </Box>
  );
}
