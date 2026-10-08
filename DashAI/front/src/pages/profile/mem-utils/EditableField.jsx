import React, { useState } from "react";
import PropTypes from "prop-types";
import Box from "@mui/material/Box";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import EditButton from "./EditButton";
import FormActions from "./FormActions";

/**
 * Label / value pair that can be switched to an inline text input.
 * `onSave` receives the trimmed new value.
 */
export default function EditableField({
  label,
  value,
  onSave,
  description,
  placeholder = "Sin información",
  multiline = false,
  required = false,
}) {
  const theme = useTheme();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);

  const startEditing = () => {
    setDraft(value);
    setEditing(true);
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    onSave(draft.trim());
    setEditing(false);
  };

  const invalid = required && draft.trim() === "";

  return (
    <Box sx={{ "& + &": { mt: 3 } }}>
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 1 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="body2"
            sx={{ color: theme.palette.text.secondary }}
          >
            {label}
          </Typography>

          {!editing && (
            <Typography
              variant="body2"
              sx={{
                color: value
                  ? theme.palette.text.primary
                  : theme.palette.text.disabled,
                mt: 0.5,
                lineHeight: 1.6,
                overflowWrap: "anywhere",
              }}
            >
              {value || placeholder}
            </Typography>
          )}
        </Box>

        {!editing && <EditButton onClick={startEditing} />}
      </Box>

      {editing && (
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 1 }}>
          <TextField
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Escape") setEditing(false);
            }}
            size="small"
            fullWidth
            autoFocus
            multiline={multiline}
            minRows={multiline ? 3 : undefined}
            error={invalid}
            helperText={invalid ? "Este campo es obligatorio." : description}
          />
          <FormActions
            onCancel={() => setEditing(false)}
            disabled={invalid}
            sx={{ mt: 1 }}
          />
        </Box>
      )}
    </Box>
  );
}

EditableField.propTypes = {
  label: PropTypes.node.isRequired,
  value: PropTypes.string.isRequired,
  onSave: PropTypes.func.isRequired,
  description: PropTypes.node,
  placeholder: PropTypes.node,
  multiline: PropTypes.bool,
  required: PropTypes.bool,
};
