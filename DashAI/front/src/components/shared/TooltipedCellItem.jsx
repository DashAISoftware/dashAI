import React from "react";
import PropTypes from "prop-types";
import { Tooltip, IconButton } from "@mui/material";

function TooltipedCellItem({
  icon,
  tooltip,
  label,
  tooltipProps = {},
  onClick,
  disabled = false,
  ...props
}) {
  return (
    <Tooltip title={tooltip} {...tooltipProps}>
      <span>
        <IconButton
          size="small"
          aria-label={label}
          onClick={onClick}
          disabled={disabled}
          {...props}
        >
          {icon}
        </IconButton>
      </span>
    </Tooltip>
  );
}

TooltipedCellItem.propTypes = {
  icon: PropTypes.element.isRequired,
  tooltip: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  tooltipProps: PropTypes.object,
  onClick: PropTypes.func,
  disabled: PropTypes.bool,
};

export default TooltipedCellItem;
