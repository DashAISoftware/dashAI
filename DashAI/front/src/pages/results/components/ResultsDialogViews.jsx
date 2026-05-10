import React from "react";
import PropTypes from "prop-types";
import { Grid, Button, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import TimestampWrapper from "../../../components/shared/TimestampWrapper";
import { TIMESTAMP_KEYS } from "../../../constants/timestamp";
import { useTranslation } from "react-i18next";

function ResultsDialogViews({ showTable, handleShowTable, handleShowGraphs }) {
  const { t } = useTranslation(["models", "common"]);

  const theme = useTheme();
  return (
    <Grid container direction="column" alignItems="center">
      <Grid container justifyContent="flex-start" sx={{ mt: 4, mb: 4 }}>
        <Grid sx={{ ml: 4 }}>
          <Typography variant="body1">
            {t("models:label.viewResultsAs")}
          </Typography>
        </Grid>
      </Grid>
      <Grid sx={{ my: 4 }} data-tour="exp-results-view-tabs">
        <Grid container justifyContent="center">
          <TimestampWrapper eventName={TIMESTAMP_KEYS.experiments.viewGraphs}>
            <Button
              variant="contained"
              color={showTable ? "primary" : "inherit"}
              onClick={handleShowTable}
              style={{
                border: `2px solid ${theme.palette.primary.main}`,
                color: showTable
                  ? theme.palette.text.primary
                  : theme.palette.primary.main,
                borderRadius: "1px",
              }}
            >
              {t("common:columns")}
            </Button>
          </TimestampWrapper>
          <TimestampWrapper eventName={TIMESTAMP_KEYS.experiments.viewGraphs}>
            <Button
              variant="contained"
              color={!showTable ? "primary" : "inherit"}
              onClick={handleShowGraphs}
              style={{
                border: `2px solid ${theme.palette.primary.main}`,
                color: !showTable
                  ? theme.palette.text.primary
                  : theme.palette.primary.main,
                borderRadius: "1px",
              }}
            >
              {t("common:graphs")}
            </Button>
          </TimestampWrapper>
        </Grid>
      </Grid>
    </Grid>
  );
}

ResultsDialogViews.propTypes = {
  showTable: PropTypes.bool.isRequired,
  handleShowTable: PropTypes.func.isRequired,
  handleShowGraphs: PropTypes.func.isRequired,
};

export default ResultsDialogViews;
