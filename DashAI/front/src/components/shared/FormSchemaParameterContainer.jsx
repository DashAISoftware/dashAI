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
          height: "auto",
          width: "inherit",
          transition: "opacity 0.3s ease",
        }}
      >
        {children}
      </Box>
    );
  }

  return (
    <BoxWithTitle title={t("common:parameters")}>
      <Box
        sx={{
          px: 2,
          overflowY: "auto",
          py: 4,
          height: "auto",
          width: "inherit",
          transition: "opacity 0.3s ease",
        }}
      >
        {children}
      </Box>
    </BoxWithTitle>
  );
}

FormSchemaParameterContainer.propTypes = {
  children: PropTypes.node.isRequired,
  showBorder: PropTypes.bool,
};

export default FormSchemaParameterContainer;
