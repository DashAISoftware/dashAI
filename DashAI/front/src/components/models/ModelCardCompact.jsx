import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Paper,
  Box,
  Typography,
  Chip,
  IconButton,
  Button,
  Tooltip,
} from "@mui/material";
import { useTheme, alpha } from "@mui/material/styles";
import { PlayArrow, Delete } from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { getRunStatus, getRunStatusColor } from "../../utils/runStatus";
import { ModelIcon } from "./model/ModelIcon";
import DeleteConfirmationModal from "../threeSectionLayout/DeleteConfirmationModal";

/**
 * Compact launcher card for a single run — shows just enough to identify
 * the model and its state, and opens the full-screen model detail view.
 */
function ModelCardCompact({
  run,
  models = [],
  onTrain,
  onDelete,
  onOpen,
  isHighlighted = false,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);

  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;
  const statusText = getRunStatus(run.status, t);
  const canTrain = run.status === 0 || run.status === 3 || run.status === 4;
  const isRunning = run.status === 1 || run.status === 2;

  const primaryMetric = (() => {
    if (!run.trained_models || run.trained_models.length === 0) return null;
    const values = {};
    run.trained_models.forEach((tm) => {
      if (!tm.metrics) return;
      Object.entries(tm.metrics).forEach(([key, value]) => {
        if (!values[key]) values[key] = [];
        values[key].push(value);
      });
    });
    const keys = Object.keys(values);
    if (keys.length === 0) return null;
    const key =
      run.goal_metric && values[run.goal_metric] ? run.goal_metric : keys[0];
    const avg = values[key].reduce((sum, v) => sum + v, 0) / values[key].length;
    return { key, avg };
  })();

  return (
    <Paper
      elevation={isHighlighted ? 4 : 1}
      onClick={onOpen}
      sx={{
        p: 3,
        display: "flex",
        flexDirection: "column",
        gap: 2,
        cursor: "pointer",
        border: 1,
        borderColor: "divider",
        borderLeft: "4px solid",
        borderLeftColor:
          run.status === 3
            ? "success.main"
            : run.status === 4
              ? "error.main"
              : isRunning
                ? "info.main"
                : "divider",
        transition: "border-color 0.15s, box-shadow 0.15s",
        "&:hover": { borderColor: "secondary.main" },
        ...(isHighlighted && {
          boxShadow: `0 0 0 3px ${alpha(theme.palette.primary.main, 0.4)}`,
        }),
      }}
    >
      <Box sx={{ display: "flex", alignItems: "flex-start", gap: 2 }}>
        <Box
          sx={{
            p: 2,
            borderRadius: 1,
            bgcolor: "action.hover",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <ModelIcon
            iconName={model?.metadata?.icon}
            color={model?.color || model?.metadata?.color}
          />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="subtitle2" noWrap sx={{ fontWeight: 600 }}>
            {modelDisplayName}
          </Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {run.name}
          </Typography>
        </Box>
      </Box>

      <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
        <Chip
          label={statusText}
          color={getRunStatusColor(run.status)}
          size="small"
        />
        {primaryMetric && (
          <Typography variant="caption" color="text.secondary">
            {primaryMetric.key.toUpperCase()}:{" "}
            <Typography component="span" variant="caption" fontWeight="medium">
              {primaryMetric.avg.toFixed(4)}
            </Typography>
          </Typography>
        )}
      </Box>

      <Box
        sx={{ display: "flex", justifyContent: "flex-end", gap: 1 }}
        onClick={(e) => e.stopPropagation()}
      >
        {canTrain && (
          <Tooltip
            title={
              run.status === 3 ? t("common:retrain") : t("common:trainVerb")
            }
          >
            <Button
              variant="outlined"
              size="small"
              startIcon={<PlayArrow fontSize="small" />}
              onClick={() => onTrain(run)}
            >
              {run.status === 3 ? t("common:retrain") : t("common:trainVerb")}
            </Button>
          </Tooltip>
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

      <DeleteConfirmationModal
        open={deleteConfirmOpen}
        onClose={() => setDeleteConfirmOpen(false)}
        onConfirm={() => {
          setDeleteConfirmOpen(false);
          localStorage.removeItem(`run-${run.id}-results-visible`);
          localStorage.removeItem(`run-${run.id}-active-tab`);
          onDelete(run);
        }}
        content={t("models:message.confirmDeleteRun")}
      />
    </Paper>
  );
}

ModelCardCompact.propTypes = {
  run: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    model_name: PropTypes.string,
    status: PropTypes.number,
    goal_metric: PropTypes.string,
    trained_models: PropTypes.array,
  }).isRequired,
  models: PropTypes.array,
  onTrain: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onOpen: PropTypes.func.isRequired,
  isHighlighted: PropTypes.bool,
};

export default ModelCardCompact;
