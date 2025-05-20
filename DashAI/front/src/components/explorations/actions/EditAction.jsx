import React from "react";
import PropTypes from "prop-types";

import { Edit as ActionIcon } from "@mui/icons-material";
import TooltipedCellItem from "../../shared/TooltipedCellItem";

const tooltips = {
  enabled: "Edit Exploration",
  disabled: "disabled",
};

function EditAction({ onAction = () => {}, disabled = false, ...props }) {
  const handleAction = () => {
    if (disabled) return;
    onAction();
  };

  const { color, tooltip } = (() => {
    switch (disabled) {
      case true:
        return { color: "", tooltip: tooltips.disabled };
      case false:
        return { color: "primary.main", tooltip: tooltips.enabled };
      default:
        return { color: "", tooltip: "" };
    }
  })();

  return (
    <React.Fragment>
      <TooltipedCellItem
        sx={{ color: color }}
        key="edit-exploration"
        icon={<ActionIcon />}
        tooltip={tooltip}
        label="Edit Exploration"
        disabled={disabled}
        {...props}
        onClick={handleAction}
      />
    </React.Fragment>
  );
}

EditAction.propTypes = {
  onAction: PropTypes.func,
  disabled: PropTypes.bool,
};

export default EditAction;
