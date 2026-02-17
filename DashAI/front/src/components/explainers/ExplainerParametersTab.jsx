import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Grid,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import ParameterListItem from "./ParameterListItem";
import { useTranslation } from "react-i18next";

/**
 * Component that displays the parameters associated with a explainer.
 * @param {object} explainerData object that contains all the necesary info of the explainer
 */
function ExplainerParametersTab({ explainerData }) {
  const [displayMode, setDisplayMode] = useState("nested-list");
  const { t } = useTranslation(["common"]);
  return (
    <Grid container direction="column">
      {/* Toggle to select the mode of displaying the JSON object. */}
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

      {/* JSON object display */}
      <Grid>
        {displayMode === "nested-list" && (
          <ParameterListItem
            name={t("common:parameters")}
            value={explainerData.parameters}
          />
        )}

        {displayMode === "json" && (
          <Typography variant="body1" component="pre">
            {JSON.stringify(explainerData.parameters, null, 4)}
          </Typography>
        )}
      </Grid>
    </Grid>
  );
}

ExplainerParametersTab.propTypes = {
  explainerData: PropTypes.shape({
    parameters: PropTypes.objectOf(
      PropTypes.oneOfType([
        PropTypes.number,
        PropTypes.string,
        PropTypes.arrayOf(PropTypes.string),
      ]),
    ),
  }).isRequired,
};

export default ExplainerParametersTab;
