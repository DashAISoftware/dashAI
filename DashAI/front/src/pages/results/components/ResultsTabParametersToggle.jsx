import React from "react";
import PropTypes from "prop-types";
import { Grid, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useTranslation } from "react-i18next";

function ResultsTabParametersToggle({ displayMode, setDisplayMode }) {
  const { t } = useTranslation(["common"]);

  return (
    <Grid>
      <ToggleButtonGroup
        value={displayMode}
        exclusive
        onChange={(event, newMode) => {
          if (newMode !== null) {
            setDisplayMode(newMode);
          }
        }}
        sx={{ float: "right" }}
      >
        <ToggleButton value="nested-list">{t("common:list")}</ToggleButton>
        <ToggleButton value="json">{t("common:json")}</ToggleButton>
      </ToggleButtonGroup>
    </Grid>
  );
}

ResultsTabParametersToggle.propTypes = {
  displayMode: PropTypes.oneOf(["nested-list", "json"]).isRequired,
  setDisplayMode: PropTypes.func.isRequired,
};

export default ResultsTabParametersToggle;
