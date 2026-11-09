import React, { useCallback, useEffect, useState } from "react";
import PropTypes from "prop-types";
import { CircularProgress, Box, Typography } from "@mui/material";
import { enqueueSnackbar } from "notistack";
import {
  deleteRunPlotOverride,
  getRunPlots,
  saveRunPlotOverride,
} from "../../api/run";
import { patchArtifactPayload } from "../../utils/artifactOverrides";
import ArtifactViewer from "../shared/ArtifactViewer";

const VIEW = "hyperparameter";

function HyperparameterPlots({ run }) {
  const [plots, setPlots] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchPlots = useCallback(async () => {
    try {
      setPlots(await getRunPlots(run.id, VIEW));
    } catch (error) {
      setPlots([]);
      if (error?.response?.status !== 404) {
        enqueueSnackbar("Error while trying to obtain hyperparameter plots", {
          variant: "error",
        });
        console.error("Error loading hyperparameter plots:", error);
      }
    }
  }, [run.id]);

  useEffect(() => {
    if (run.status === 3) {
      setLoading(true);
      fetchPlots().finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [run.id, run.status, fetchPlots]);

  const handleSaveOverride = async (index, figure) => {
    try {
      await saveRunPlotOverride(run.id, VIEW, index, figure);
      setPlots((prev) =>
        patchArtifactPayload(prev, index, JSON.stringify(figure)),
      );
    } catch (error) {
      console.error("Error saving hyperparameter plot override:", error);
    }
  };

  const handleResetOverride = async (index) => {
    try {
      await deleteRunPlotOverride(run.id, VIEW, index);
      await fetchPlots();
    } catch (error) {
      console.error("Error resetting hyperparameter plot override:", error);
    }
  };

  if (loading) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (run.status === 2 || run.status === 1) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          Training in progress. Hyperparameter plots will be available when
          training completes.
        </Typography>
      </Box>
    );
  }

  if (run.status === 4) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="error">
          Run failed. No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  if (run.status === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          Run not started. No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  if (plots.length === 0) {
    return (
      <Box
        sx={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 400,
        }}
      >
        <Typography color="textSecondary">
          No hyperparameter plots available.
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 4 }}>
      <Box
        sx={{
          display: "grid",
          gap: 4,
          gridTemplateColumns: "repeat(auto-fit, minmax(600px, 1fr))",
        }}
      >
        {plots.map((artifact, position) => (
          <ArtifactViewer
            key={artifact.index}
            artifact={artifact}
            siblingArtifacts={plots}
            siblingIndex={position}
            canReset={Boolean(artifact.overridden)}
            onSaveEdit={(figure) => handleSaveOverride(artifact.index, figure)}
            onResetEdit={() => handleResetOverride(artifact.index)}
          />
        ))}
      </Box>
    </Box>
  );
}

HyperparameterPlots.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.number.isRequired,
  }).isRequired,
};

export default HyperparameterPlots;
