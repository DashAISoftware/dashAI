import React from "react";
import { DialogContentText, Grid, Paper } from "@mui/material";
import PropTypes from "prop-types";

import ParameterForm from "../configurableObject/ParameterForm";
import { useTranslation } from "react-i18next";

function ExplainerConfiguration({ paramsSchema, updateParameters }) {
  const { t } = useTranslation(["explainers"]);

  return (
    <Paper
      variant="outlined"
      sx={{ p: 8, maxHeight: "55vh", overflow: "auto" }}
    >
      <Grid container direction={"column"} alignItems={"center"}>
        {/* Form title */}
        <Grid>
          <DialogContentText>
            {t("explainers:label.explainerConfiguration")}
          </DialogContentText>
        </Grid>
        <Grid sx={{ p: 6 }}>
          {/* Main dataloader form */}
          <ParameterForm
            parameterSchema={paramsSchema}
            onFormSubmit={updateParameters}
          />
        </Grid>
      </Grid>
    </Paper>
  );
}

ExplainerConfiguration.propTypes = {
  paramsSchema: PropTypes.objectOf(
    PropTypes.oneOfType([PropTypes.string, PropTypes.bool, PropTypes.object]),
  ).isRequired,
  updateParameters: PropTypes.func,
};

export default ExplainerConfiguration;
