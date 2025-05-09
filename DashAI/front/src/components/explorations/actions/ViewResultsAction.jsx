import React from "react";
import PropTypes from "prop-types";

import { QueryStats as ActionIcon } from "@mui/icons-material";
import TooltipedCellItem from "../../shared/TooltipedCellItem";

const tooltips = {
  enabled: "View Results",
  disabled: "disabled",
};

function ViewResultsAction({
  onAction = () => {},
  disabled = false,
  ...props
}) {
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
        key="results-exploration"
        icon={<ActionIcon />}
        tooltip={tooltip}
        label="View Results"
        disabled={disabled}
        {...props}
        onClick={handleAction}
      />
    </React.Fragment>
  );
}

ViewResultsAction.propTypes = {
  onSelect: PropTypes.func,
  disabled: PropTypes.bool,
};

export default ViewResultsAction;
