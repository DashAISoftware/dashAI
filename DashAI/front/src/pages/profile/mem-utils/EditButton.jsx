import React from "react";
import PropTypes from "prop-types";
import Button from "@mui/material/Button";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";

/**
 * Primary-colored text button used to start editing a field.
 */
export default function EditButton({
  children = "Editar",
  withIcon = true,
  onClick,
  disabled = false,
  sx,
}) {
  return (
    <Button
      variant="text"
      size="small"
      onClick={onClick}
      disabled={disabled}
      startIcon={withIcon ? <EditOutlinedIcon /> : null}
      sx={{ flexShrink: 0, textTransform: "none", ...sx }}
    >
      {children}
    </Button>
  );
}

EditButton.propTypes = {
  children: PropTypes.node,
  withIcon: PropTypes.bool,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
  sx: PropTypes.object,
};
