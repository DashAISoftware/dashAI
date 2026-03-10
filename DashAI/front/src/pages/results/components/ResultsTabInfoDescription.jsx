import React from "react";
import PropTypes from "prop-types";
import { Grid, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

function ResultsTabInfoDescription({ runData }) {
  const { t } = useTranslation(["common"]);
  return (
    <Grid>
      <Typography variant="subtitle1">{t("common:description")}</Typography>
      <Typography variant="p" sx={{ color: "gray" }}>
        {runData.description ?? "-"}
      </Typography>
    </Grid>
  );
}

ResultsTabInfoDescription.propTypes = {
  runData: PropTypes.object.isRequired,
};

export default ResultsTabInfoDescription;
