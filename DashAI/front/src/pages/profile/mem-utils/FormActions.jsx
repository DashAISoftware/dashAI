import React from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";

/**
 * Submit / cancel buttons placed at the bottom of an edit form.
 * The submit button is `type="submit"`, so it must live inside a <form>.
 */
export default function FormActions({
  onCancel,
  submitLabel = "Guardar",
  cancelLabel = "Cancelar",
  disabled = false,
  sx,
}) {
  return (
    <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end", ...sx }}>
      <Button
        variant="text"
        size="small"
        onClick={onCancel}
        sx={{ textTransform: "none" }}
      >
        {cancelLabel}
      </Button>
      <Button
        type="submit"
        variant="contained"
        size="small"
        disabled={disabled}
        disableElevation
        sx={{ textTransform: "none" }}
      >
        {submitLabel}
      </Button>
    </Box>
  );
}

FormActions.propTypes = {
  onCancel: PropTypes.func.isRequired,
  submitLabel: PropTypes.node,
  cancelLabel: PropTypes.node,
  disabled: PropTypes.bool,
  sx: PropTypes.object,
};
