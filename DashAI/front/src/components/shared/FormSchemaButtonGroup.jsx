import { Button, ButtonGroup } from "@mui/material";
import { t } from "i18next";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText = t("common:save"),
  backButtonText = t("common:back"),
  dataTour,
}) {
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
    <ButtonGroup
      size="large"
      sx={{
        justifyContent: "flex-end",
        width: "100%",
        display: "flex",
        mt: 3,
      }}
    >
      {onCancel && (
        <Button variant="outlined" onClick={onCancel}>
          {backButtonText}
        </Button>
      )}
      {!autoSave && (
        <Button
          variant="contained"
          onClick={() => onFormSubmit(formik?.values)}
          disabled={Object.keys(formik?.errors ?? {}).length > 0 || error}
          data-tour={finalDataTour}
        >
          {saveButtonText}
        </Button>
      )}
    </ButtonGroup>
  );
}

export default FormSchemaButtonGroup;
