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
import { PlayArrow, Delete, Info } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import ModelsBreadcrumbs from "./ModelsBreadcrumbs";
import RunCard from "./RunCard";
import InfoModal from "../shared/InfoModal";
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
 * Full-screen detail view for a single model run: header with the run's
 * identity and actions, an info modal with quick facts, and RunCard's tabs
 * below. The column layout keeps the header fixed and lets RunCard (in
 * fillHeight mode) own the scroll.
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
  profiles,
  selectedProfile,
  onProfileChange,
}) {
  const { t, i18n } = useTranslation(["models", "common"]);
  const [infoModalOpen, setInfoModalOpen] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;
  const statusText = getRunStatus(run.status, t);
  const canTrain = run.status === 0 || run.status === 3 || run.status === 4;
  const isRunning = run.status === 1 || run.status === 2;

  const createdLabel = formatCreatedDate(run.created, i18n.language);
  const durationLabel = formatDuration(run.start_time, run.end_time);

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        height: "100%",
        minHeight: 0,
      }}
    >
      <Box sx={{ flexShrink: 0, px: 4, pt: 4 }}>
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

          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
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
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Tooltip title={t("common:info")}>
                <IconButton
                  size="small"
                  sx={{ p: 0.5 }}
                  onClick={() => setInfoModalOpen(true)}
                >
                  <Info fontSize="small" />
                </IconButton>
              </Tooltip>
              <Tooltip title={t("models:button.deleteRun")}>
                <IconButton
                  size="small"
                  color="error"
                  sx={{ p: 0.5 }}
                  disabled={isRunning}
                  onClick={() => setDeleteConfirmOpen(true)}
                >
                  <Delete fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
        </Box>
      </Box>

      <Box
        sx={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          px: 4,
          pb: 4,
        }}
      >
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
          profiles={profiles}
          selectedProfile={selectedProfile}
          onProfileChange={onProfileChange}
        />
      </Box>

      <InfoModal
        title={t("common:runInformation")}
        subtitle={run.name}
        rows={[
          { label: t("common:id"), value: run.id },
          { label: t("common:model"), value: modelDisplayName },
          {
            label: t("common:associatedDataset"),
            value: datasetName || t("common:unknown"),
          },
          {
            label: t("common:createdAt"),
            value: createdLabel || t("common:unknown"),
          },
          {
            label: t("common:duration"),
            value: durationLabel || t("common:unknown"),
          },
        ]}
        open={infoModalOpen}
        onClose={() => setInfoModalOpen(false)}
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
  profiles: PropTypes.array,
  selectedProfile: PropTypes.string,
  onProfileChange: PropTypes.func,
};
