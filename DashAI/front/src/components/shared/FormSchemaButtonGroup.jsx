import { Button, ButtonGroup } from "@mui/material";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText = "Save",
  backButtonText = "Back",
  className = "",
}) {
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
          className={`${className}-save create-notebook-button`}
        >
          {saveButtonText}
        </Button>
      )}
    </ButtonGroup>
  );
}

export default FormSchemaButtonGroup;
