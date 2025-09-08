import { Button, ButtonGroup, Typography } from "@mui/material";
import React from "react";

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
        >
          {saveButtonText}
        </Button>
      )}
    </ButtonGroup>
  );
}

export default FormSchemaButtonGroup;
