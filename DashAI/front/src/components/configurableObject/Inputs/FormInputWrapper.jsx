import { Box } from "@mui/material";
import PropTypes from "prop-types";
import React from "react";
import FormTooltip from "../FormTooltip";
import { useFormCard } from "../../../contexts/FormCardContext";

/**
 * Generic component that wraps each form input.
 * When rendered inside a FormSchemaFieldCard the tooltip is suppressed (the card header
 * already shows it) and the input expands to full width.
 *
 * @param {string}  description      text to put in the tooltip
 * @param {boolean} disabledPadding  if true, removes the top padding on the tooltip box
 * @param {node}    children         the input component to render
 */
function FormInputWrapper({ description, disabledPadding = false, children }) {
  const isInCard = useFormCard();

  if (isInCard) {
    return <Box width="100%">{children}</Box>;
  }

  return (
    <Box display="flex" alignItems="flex-start" gap={4} width="100%">
      <Box sx={{ flex: 1, width: "80%" }}>{children}</Box>
      <Box sx={{ pt: disabledPadding ? 0 : 4, width: "auto" }}>
        <FormTooltip contentStr={description} />
      </Box>
    </Box>
  );
}

FormInputWrapper.propTypes = {
  description: PropTypes.string,
  disabledPadding: PropTypes.bool,
  children: PropTypes.node.isRequired,
};

export default FormInputWrapper;
