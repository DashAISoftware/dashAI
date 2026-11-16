import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { Alert, Box, CircularProgress } from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  deleteRunPlotOverride,
  getRunPlots,
  saveRunPlotOverride,
} from "../../api/run";
import { getApiErrorMessage } from "../../utils/apiError";
import { patchArtifactPayload } from "../../utils/artifactOverrides";
import ArtifactList from "../shared/ArtifactList";

const VIEW = "forecasts";

/**
 * The forecasts a finished backtest run saved, drawn at training time and
 * shown in the shared artifact cards (GET /run/{id}/plots/forecasts): one
 * figure per origin with the actual values, the forecast and its intervals
 * by level. Edits to a figure are saved with the run.
 *
 * Shown for a strategy whose `result_views` declares "forecasts".
 */
export default function ForecastsChart({ run }) {
  const { t } = useTranslation(["models", "common"]);
  const [items, setItems] = useState(null);
  const [error, setError] = useState(null);

  const fetchPlots = useCallback(
    () => getRunPlots(run.id, VIEW).then(setItems),
    [run.id],
  );

  useEffect(() => {
    let cancelled = false;
    setItems(null);
    setError(null);
    getRunPlots(run.id, VIEW)
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
  }, [run.id]);

  const handleSaveOverride = async (index, figure) => {
    try {
      await saveRunPlotOverride(run.id, VIEW, index, figure);
      setItems((prev) =>
        patchArtifactPayload(prev, index, JSON.stringify(figure)),
      );
    } catch (err) {
      console.error("Error saving forecasts plot override:", err);
    }
  };

  const handleResetOverride = async (index) => {
    try {
      await deleteRunPlotOverride(run.id, VIEW, index);
      await fetchPlots();
    } catch (err) {
      console.error("Error resetting forecasts plot override:", err);
    }
  };

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

  return (
    <ArtifactList
      items={items}
      ctx={{
        onSaveOverride: handleSaveOverride,
        onResetOverride: handleResetOverride,
      }}
    />
  );
}

ForecastsChart.propTypes = {
  run: PropTypes.shape({ id: PropTypes.number.isRequired }).isRequired,
};
