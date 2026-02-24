import React from "react";
import PropTypes from "prop-types";
import { Grid, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useTranslation } from "react-i18next";

function ResultsTabMetricsToggle({ displaySet, setDisplaySet }) {
  const { t } = useTranslation(["common"]);

  return (
    <Grid>
      <ToggleButtonGroup
        value={displaySet}
        exclusive
        onChange={(event, newSet) => {
          // condition to enforce value set
          if (newSet !== null) {
            setDisplaySet(newSet);
          }
        }}
        sx={{ float: "right" }}
      >
        <ToggleButton value="test_metrics">{t("common:test")}</ToggleButton>
        <ToggleButton value="train_metrics">{t("common:train")}</ToggleButton>
        <ToggleButton value="validation_metrics">
          {t("common:validation")}
        </ToggleButton>
      </ToggleButtonGroup>
    </Grid>
  );
}

ResultsTabMetricsToggle.propTypes = {
  displaySet: PropTypes.string.isRequired,
  setDisplaySet: PropTypes.func.isRequired,
};

export default ResultsTabMetricsToggle;
