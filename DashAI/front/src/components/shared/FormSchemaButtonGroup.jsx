import { Button, ButtonGroup } from "@mui/material";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText = "Save",
  backButtonText = "Back",
  dataTour,
}) {
  const isCreateExplorer = saveButtonText === "Create Explorer";
  const isCreateConverter = saveButtonText === "Create Converter";
  const finalDataTour =
    dataTour ||
    (isCreateExplorer
      ? "create-explorer-button"
      : isCreateConverter
        ? "create-converter-button"
        : undefined);

  return (
    <ButtonGroup size="large" sx={{ justifyContent: "flex-end" }}>
      {onCancel && (
        <Button variant="outlined" onClick={onCancel}>
          {backButtonText}
        </Button>
      )}
      {!autoSave && (
        <Button
          variant="contained"
          onClick={onFormSubmit}
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
