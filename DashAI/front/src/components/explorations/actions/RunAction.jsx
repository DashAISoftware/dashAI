import React from "react";
import PropTypes from "prop-types";

import { PlayArrow as ActionIcon } from "@mui/icons-material";
import TooltipedCellItem from "../../shared/TooltipedCellItem";

const tooltips = {
  enabled: "Run the exploration",
  disabled: "The exploration cannot be run right now",
};

function RunAction({ onAction, disabled = false, ...props }) {
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
        key="run-exploration"
        icon={<ActionIcon />}
        tooltip={tooltip}
        label="Run Exploration"
        disabled={disabled}
        {...props}
        onClick={handleAction}
      />
    </React.Fragment>
  );
}

RunAction.propTypes = {
  onAction: PropTypes.func,
  disabled: PropTypes.bool,
};

export default RunAction;
