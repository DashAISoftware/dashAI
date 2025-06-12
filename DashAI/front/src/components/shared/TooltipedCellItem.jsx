import React from "react";
import PropTypes from "prop-types";

import { Tooltip } from "@mui/material";
import { GridActionsCellItem } from "@mui/x-data-grid";

/**
 * Component that wraps a GridActionsCellItem with a Tooltip.
 * @param {object} props the props of the component.
 * @param {element} props.icon the icon of the item.
 * @param {string} props.tooltip the text of the tooltip.
 * @param {string} props.label the label of the item.
 * @param {object} props.tooltipProps the props of the tooltip.
 */
function TooltipedCellItem({
  icon,
  tooltip,
  label,
  tooltipProps = {},
  ...props
}) {
  return (
    <Tooltip title={tooltip} {...tooltipProps}>
      {/* This span allows tooltip when the element is disabled */}
      <span>
        <GridActionsCellItem icon={icon} label={label} {...props} />
      </span>
    </Tooltip>
  );
}

TooltipedCellItem.propTypes = {
  icon: PropTypes.element.isRequired,
  tooltip: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  tooltipProps: PropTypes.object,
};

export default TooltipedCellItem;
