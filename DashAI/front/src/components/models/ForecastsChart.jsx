import React, { useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Alert, Box, CircularProgress } from "@mui/material";
import { useTranslation } from "react-i18next";
import { getRunForecastsPlot } from "../../api/run";
import { getApiErrorMessage } from "../../utils/apiError";
import ArtifactList from "../shared/ArtifactList";

/**
 * The forecasts a finished backtest run saved, drawn server side as plotly
 * artifacts (GET /run/{id}/forecasts/plot) and shown in the shared artifact
 * cards: one figure per origin with the actual values, the forecast and its
 * intervals by level.
 *
 * Shown for a strategy whose `result_views` declares "forecasts".
 */
export default function ForecastsChart({ run }) {
  const { t, i18n } = useTranslation(["models", "common"]);
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setError(null);
    getRunForecastsPlot(run.id)
      .then((data) => {
        if (!cancelled) setItems(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(getApiErrorMessage(err, t("common:unknownError")));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [run.id, i18n.language]);

  if (error) {
    return <Alert severity="info">{error}</Alert>;
  }
  if (!items) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return <ArtifactList items={items} />;
}

ForecastsChart.propTypes = {
  run: PropTypes.shape({ id: PropTypes.number.isRequired }).isRequired,
};
