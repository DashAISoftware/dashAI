import React from "react";
import PropTypes from "prop-types";
import { Switch, Typography, Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useTheme } from "@mui/material/styles";

function ResultsGraphsSwitch({ showCustomMetrics, handleToggleMetrics }) {
  const { t } = useTranslation(["models"]);
  const theme = useTheme();
  return (
    <Box mb={2} display="flex" justifyContent="flex-start" width="100%">
      <Box display="flex" alignItems="center">
        <Typography variant="subtitle2" style={{ fontSize: "0.8rem" }}>
          {t("models:label.generalMetrics")}
        </Typography>
      </Box>
      <Box display="flex" alignItems="center">
        <Switch
          checked={showCustomMetrics}
          onChange={handleToggleMetrics}
          color="primary"
          sx={{
            "& .MuiSwitch-thumb": {
              backgroundColor: theme.palette.primary.main,
            },
          }}
          name="metricsSwitch"
          inputProps={{ "aria-label": "Cambiar métricas" }}
        />
      </Box>
      <Box display="flex" alignItems="center">
        <Typography variant="subtitle2" style={{ fontSize: "0.8rem" }}>
          {t("models:label.customMetrics")}
        </Typography>
      </Box>
    </Box>
  );
}

ResultsGraphsSwitch.propTypes = {
  showCustomMetrics: PropTypes.bool.isRequired,
  handleToggleMetrics: PropTypes.func,
};

export default ResultsGraphsSwitch;
