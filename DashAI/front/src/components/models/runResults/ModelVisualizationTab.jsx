import React, { useCallback, useEffect, useRef, useState } from "react";
import PropTypes from "prop-types";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Typography,
} from "@mui/material";
import AutoGraphIcon from "@mui/icons-material/AutoGraph";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useTranslation } from "react-i18next";
import { useSnackbar } from "notistack";

import { getRunModelArtifacts } from "../../../api/run";
import { enqueueModelVisualizationJob } from "../../../api/job";
import ArtifactList from "../../shared/ArtifactList";

/** How often the tab re-reads the endpoint while a generation is in flight. */
const POLL_INTERVAL_MS = 3000;

/** Backend statuses that mean the job is queued or running. */
const IN_FLIGHT = ["DELIVERED", "STARTED"];

/**
 * Shows how a trained model looks: the tree it learned, the weights it fitted,
 * the surface it decides on. The artifacts are produced on demand by
 * ModelVisualizationJob, so this tab offers a Generate button, follows the
 * job by polling the run's artifact endpoint, and renders whatever came back.
 *
 * Generation state is read from the server rather than kept locally, so a
 * reload during a long generation still shows it as in progress.
 */
export default function ModelVisualizationTab({ run }) {
  const { t } = useTranslation(["models", "common"]);
  const { enqueueSnackbar } = useSnackbar();

  const [artifacts, setArtifacts] = useState([]);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enqueuing, setEnqueuing] = useState(false);
  const pollRef = useRef(null);

  const fetchArtifacts = useCallback(async () => {
    try {
      const response = await getRunModelArtifacts(run.id.toString());
      setArtifacts(response.artifacts ?? []);
      setStatus(response.status ?? null);
      return response.status ?? null;
    } catch (error) {
      console.error("Error fetching model artifacts:", error);
      enqueueSnackbar(t("models:message.visualizationFetchFailed"), {
        variant: "error",
      });
      return null;
    }
  }, [run.id, enqueueSnackbar, t]);

  useEffect(() => {
    setLoading(true);
    fetchArtifacts().finally(() => setLoading(false));
  }, [fetchArtifacts]);

  const generating = enqueuing || IN_FLIGHT.includes(status);

  // Poll only while a generation is outstanding, and stop as soon as the
  // status settles so an idle tab makes no requests.
  useEffect(() => {
    if (!generating) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return undefined;
    }
    pollRef.current = setInterval(fetchArtifacts, POLL_INTERVAL_MS);
    return () => {
      clearInterval(pollRef.current);
      pollRef.current = null;
    };
  }, [generating, fetchArtifacts]);

  const handleGenerate = async () => {
    setEnqueuing(true);
    try {
      await enqueueModelVisualizationJob(run.id);
      // Read the status straight back so the polling effect turns on even if
      // the job finished before the first interval elapsed.
      await fetchArtifacts();
    } catch (error) {
      console.error("Error enqueuing model visualization job:", error);
      enqueueSnackbar(t("models:message.visualizationFailed"), {
        variant: "error",
      });
    } finally {
      setEnqueuing(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 6 }}>
        <CircularProgress />
      </Box>
    );
  }

  const hasArtifacts = artifacts.length > 0;
  const generateLabel = hasArtifacts
    ? t("models:button.regenerateVisualization")
    : t("models:button.generateVisualization");

  return (
    <Box sx={{ py: 4, display: "flex", flexDirection: "column", gap: 3 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Button
          variant={hasArtifacts ? "outlined" : "contained"}
          size="small"
          disabled={generating}
          startIcon={hasArtifacts ? <RefreshIcon /> : <AutoGraphIcon />}
          onClick={handleGenerate}
        >
          {generateLabel}
        </Button>
        {generating && (
          <>
            <CircularProgress size={18} />
            <Typography variant="body2" color="text.secondary">
              {t("models:message.generatingVisualization")}
            </Typography>
          </>
        )}
      </Box>

      {status === "ERROR" && !generating && (
        <Alert severity="error">
          {t("models:message.visualizationFailed")}
        </Alert>
      )}

      {!hasArtifacts && !generating && status !== "ERROR" && (
        <Typography variant="body2" color="text.secondary">
          {status === "FINISHED"
            ? t("models:message.modelHasNoVisualization")
            : t("models:message.noVisualizationYet")}
        </Typography>
      )}

      {hasArtifacts && <ArtifactList items={artifacts} />}
    </Box>
  );
}

ModelVisualizationTab.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number.isRequired,
    model_name: PropTypes.string,
    status: PropTypes.number,
  }).isRequired,
};
