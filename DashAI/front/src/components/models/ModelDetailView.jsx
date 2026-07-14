import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Box,
  Typography,
  Button,
  IconButton,
  Chip,
  Tooltip,
} from "@mui/material";
import { PlayArrow, Delete } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import ModelsBreadcrumbs from "./ModelsBreadcrumbs";
import RunCard from "./RunCard";
import { getRunStatus, getRunStatusColor } from "../../utils/runStatus";

function formatCreatedDate(dateStr, locale) {
  if (!dateStr) return null;
  const date = new Date(dateStr);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(startTime, endTime) {
  if (!startTime || !endTime) return null;
  const totalSeconds = Math.max(
    0,
    Math.round((new Date(endTime) - new Date(startTime)) / 1000),
  );
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0
    ? `${minutes}m ${String(seconds).padStart(2, "0")}s`
    : `${seconds}s`;
}

/**
 * Full-screen detail view for a single model run — header with the run's
 * identity/actions, a quick-facts line, and RunResults' tabs (Configuración,
 * Métricas, Explicabilidad, Predicción, HPO) below.
 */
export default function ModelDetailView({
  run,
  models = [],
  session,
  datasetName,
  onTrain,
  onDelete,
  explainerRefreshTrigger,
  onOperationsRefresh,
  existingRuns = [],
  onRefresh,
}) {
  const { t, i18n } = useTranslation(["models", "common"]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;
  const statusText = getRunStatus(run.status, t);
  const canTrain = run.status === 0 || run.status === 3 || run.status === 4;
  const isRunning = run.status === 1 || run.status === 2;

  const createdLabel = formatCreatedDate(run.created, i18n.language);
  const durationLabel = formatDuration(run.start_time, run.end_time);

  const statsParts = [
    `${t("common:status")} ${statusText}`,
    datasetName && `${t("common:dataset")} ${datasetName}`,
    createdLabel && `${t("common:created")} ${createdLabel}`,
    durationLabel && `${t("common:duration")} ${durationLabel}`,
  ].filter(Boolean);

  return (
    <Box sx={{ px: 4, pt: 4, pb: 4 }}>
      <ModelsBreadcrumbs />

      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: 2,
          mb: 1,
        }}
      >
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 2,
            flexWrap: "wrap",
          }}
        >
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            {run.name}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {modelDisplayName}
          </Typography>
          <Chip
            label={statusText}
            color={getRunStatusColor(run.status)}
            size="small"
          />
        </Box>

        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          {canTrain && (
            <Button
              variant="contained"
              size="small"
              startIcon={<PlayArrow />}
              onClick={() => onTrain(run)}
            >
              {run.status === 3 ? t("common:retrain") : t("common:trainVerb")}
            </Button>
          )}
          <Tooltip title={t("models:button.deleteRun")}>
            <IconButton
              size="small"
              color="error"
              disabled={isRunning}
              onClick={() => setDeleteConfirmOpen(true)}
            >
              <Delete fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 4 }}>
        {statsParts.map((part, i) => (
          <React.Fragment key={i}>
            {i > 0 && " | "}
            {part}
          </React.Fragment>
        ))}
      </Typography>

      <RunCard
        run={run}
        models={models}
        session={session}
        onTrain={onTrain}
        onDelete={onDelete}
        explainerRefreshTrigger={explainerRefreshTrigger}
        onOperationsRefresh={onOperationsRefresh}
        existingRuns={existingRuns}
        onRefresh={onRefresh}
        forceExpanded
        hideChrome
        deleteConfirmOpen={deleteConfirmOpen}
        setDeleteConfirmOpen={setDeleteConfirmOpen}
      />
    </Box>
  );
}

ModelDetailView.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    created: PropTypes.string,
    start_time: PropTypes.string,
    end_time: PropTypes.string,
  }).isRequired,
  models: PropTypes.array,
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  datasetName: PropTypes.string,
  onTrain: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  explainerRefreshTrigger: PropTypes.number,
  onOperationsRefresh: PropTypes.func,
  existingRuns: PropTypes.array,
  onRefresh: PropTypes.func,
};
