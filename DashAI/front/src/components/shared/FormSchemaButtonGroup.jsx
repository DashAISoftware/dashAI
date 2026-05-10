import { Button, Box } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText,
  backButtonText,
  dataTour,
}) {
  const { t } = useTranslation(["common", "datasets"]);
  const finalSaveText = saveButtonText ?? t("common:save");
  const finalBackText = backButtonText ?? t("common:back");

  const isCreateExplorer =
    saveButtonText === t("datasets:button.createExplorer");
  const isCreateConverter =
    saveButtonText === t("datasets:button.createConverter");
  const finalDataTour =
    dataTour ||
    (isCreateExplorer
      ? "create-explorer-button"
      : isCreateConverter
        ? "create-converter-button"
        : undefined);

  return (
    <Box
      size="large"
      sx={{
        mt: 4,
        pt: 4,
        flexShrink: 0,
        display: "flex",
        justifyContent: "flex-end",
        gap: 2,
      }}
    >
      {onCancel && (
        <Button variant="outlined" onClick={onCancel}>
          {finalBackText}
        </Button>
      )}
      {!autoSave && (
        <Button
          variant="contained"
          onClick={onFormSubmit}
          disabled={Object.keys(formik?.errors ?? {}).length > 0 || error}
          data-tour={finalDataTour}
        >
          {finalSaveText}
        </Button>
      )}
    </Box>
  );
}

FormSchemaButtonGroup.propTypes = {
  onCancel: PropTypes.func,
  onFormSubmit: PropTypes.func,
  autoSave: PropTypes.bool,
  formik: PropTypes.object,
  error: PropTypes.bool,
  saveButtonText: PropTypes.string,
  backButtonText: PropTypes.string,
  dataTour: PropTypes.string,
};

export default FormSchemaButtonGroup;
