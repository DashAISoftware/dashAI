import React from "react";
import BoxWithTitle from "./BoxWithTitle";
import { Box } from "@mui/material";
import PropTypes from "prop-types";
import { useTranslation } from "react-i18next";

/**
 * This component is a container for the parameters of a model schema
 */

function FormSchemaParameterContainer({ children, showBorder = true }) {
  const { t } = useTranslation(["common"]);

  if (!showBorder) {
    return (
      <Box
        sx={{
          overflowY: "auto",
          flex: 1,
          minHeight: 0,
          width: "inherit",
          transition: "opacity 0.3s ease",
        }}
      >
        {children}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        overflowY: "auto",
        flex: 1,
        minHeight: 0,
        width: "inherit",
        transition: "opacity 0.3s ease",
      }}
    >
      {children}
    </Box>
  );
}

FormSchemaParameterContainer.propTypes = {
  children: PropTypes.node.isRequired,
  showBorder: PropTypes.bool,
};

export default FormSchemaParameterContainer;
