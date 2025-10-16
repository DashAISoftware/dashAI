import { Button, ButtonGroup } from "@mui/material";

function FormSchemaButtonGroup({
  onCancel,
  onFormSubmit,
  autoSave,
  formik,
  error,
  saveButtonText = "Save",
  backButtonText = "Back",
}) {
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
        >
          {saveButtonText}
        </Button>
      )}
    </ButtonGroup>
  );
}

export default FormSchemaButtonGroup;
