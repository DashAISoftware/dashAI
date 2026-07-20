import React, { useState } from "react";
import PropTypes from "prop-types";
import {
  Paper,
  Box,
  Typography,
  IconButton,
  Tooltip,
  CircularProgress,
} from "@mui/material";
import { useTheme, alpha } from "@mui/material/styles";
import {
  PlayArrow,
  Delete,
  WarningAmber,
  ChevronRight,
  Edit,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { getRunStatusColor } from "../../utils/runStatus";
import { ModelIcon } from "./model/ModelIcon";
import DeleteConfirmationModal from "../threeSectionLayout/DeleteConfirmationModal";
import RunEditDialog from "./RunEditDialog";

const RING_SIZE = 36;

function ScoreRing({ run, score, statusMain }) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);
  const isRunning = run.status === 1 || run.status === 2;
  const isError = run.status === 4;
  const isFinished = run.status === 3;

  if (isRunning) {
    return (
      <CircularProgress
        size={RING_SIZE}
        thickness={3.5}
        sx={{ color: statusMain }}
      />
    );
  }

  if (isError) {
    return (
      <Box
        sx={{
          position: "relative",
          width: RING_SIZE,
          height: RING_SIZE,
          flexShrink: 0,
        }}
      >
        <CircularProgress
          variant="determinate"
          value={100}
          size={RING_SIZE}
          thickness={3.5}
          sx={{ color: alpha(statusMain, 0.3) }}
        />
        <Box
          sx={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <WarningAmber sx={{ color: statusMain, fontSize: 18 }} />
        </Box>
      </Box>
    );
  }

  if (isFinished && score) {
    const rounded = Math.round(score.score);
    const tooltipContent = (
      <Typography variant="body2" component="div" sx={{ lineHeight: 1.6 }}>
        <Typography
          variant="body2"
          component="div"
          sx={{ fontWeight: "bold", mb: 1 }}
        >
          {t("models:label.score")}: {score.score.toFixed(1)}/100
        </Typography>
        {score.breakdown?.map(
          ({ metric_name, value, normalized_weight }, i) => (
            <Typography variant="body2" component="div" key={metric_name}>
              {i === 0 ? "=" : "+"} {metric_name} ({value.toFixed(4)}) ×{" "}
              {(normalized_weight * 100).toFixed(0)}%
            </Typography>
          ),
        )}
      </Typography>
    );

    return (
      <Tooltip title={tooltipContent} placement="top" arrow>
        <Box
          sx={{
            position: "relative",
            width: RING_SIZE,
            height: RING_SIZE,
            flexShrink: 0,
            cursor: "help",
          }}
        >
          <CircularProgress
            variant="determinate"
            value={100}
            size={RING_SIZE}
            thickness={3.5}
            sx={{ color: alpha(statusMain, 0.2), position: "absolute" }}
          />
          <CircularProgress
            variant="determinate"
            value={rounded}
            size={RING_SIZE}
            thickness={3.5}
            sx={{ color: statusMain }}
          />
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography sx={{ fontWeight: 700, fontSize: 12, lineHeight: 1 }}>
              {rounded}
            </Typography>
          </Box>
        </Box>
      </Tooltip>
    );
  }

  // Not started (or finished with no score yet available)
  return (
    <Box
      sx={{
        position: "relative",
        width: RING_SIZE,
        height: RING_SIZE,
        flexShrink: 0,
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          border: `2.5px dashed ${theme.palette.text.disabled}`,
          opacity: 0.4,
        }}
      />
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Typography color="text.disabled" sx={{ fontSize: 12, lineHeight: 1 }}>
          –
        </Typography>
      </Box>
    </Box>
  );
}

/**
 * Compact launcher card for a single run — shows just enough to identify
 * the model and its state, and opens the full-screen model detail view.
 */
function ModelCardCompact({
  run,
  models = [],
  score,
  session,
  existingRuns = [],
  onTrain,
  onDelete,
  onRefresh,
  onOpen,
  isHighlighted = false,
}) {
  const theme = useTheme();
  const { t } = useTranslation(["models", "common"]);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [configOpen, setConfigOpen] = useState(false);

  const model = models.find((m) => m.name === run.model_name);
  const modelDisplayName = model?.display_name || run.model_name;
  const canTrain = run.status === 0 || run.status === 3 || run.status === 4;
  const isRunning = run.status === 1 || run.status === 2;

  const statusColorKey = getRunStatusColor(run.status);
  const statusMain =
    statusColorKey === "default"
      ? theme.palette.text.disabled
      : theme.palette[statusColorKey].main;

  return (
    <Paper
      elevation={0}
      onClick={onOpen}
      sx={{
        display: "flex",
        flexDirection: "column",
        cursor: "pointer",
        border: 1,
        borderColor: alpha(statusMain, 0.35),
        transition:
          "border-color 0.15s, box-shadow 0.2s ease-out, transform 0.15s ease-out",
        "&:hover": {
          borderColor: theme.palette.primary.main,
          transform: "translateY(-3px)",
          boxShadow: `0 6px 16px ${alpha(theme.palette.common.black, 0.35)}`,
          "& .card-chevron-icon": { color: theme.palette.primary.main },
        },
        ...(isHighlighted && {
          transition:
            "border-color 0.15s, box-shadow 1.2s ease-out, transform 0.15s ease-out",
          boxShadow: `0 0 0 3px ${alpha(
            theme.palette.primary.main,
            0.4,
          )}, 0 0 20px 6px ${alpha(theme.palette.primary.main, 0.18)}`,
        }),
      }}
    >
      <Box
        sx={{
          pt: 1.5,
          pb: 2.5,
          px: 2.5,
          display: "flex",
          alignItems: "center",
          gap: 2,
        }}
      >
        <Box
          sx={{
            p: 1.5,
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
            {run.name}
          </Typography>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
            <Box
              sx={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                bgcolor: statusMain,
                flexShrink: 0,
              }}
            />
            <Typography variant="caption" color="text.secondary" noWrap>
              {modelDisplayName}
            </Typography>
          </Box>
        </Box>

        <ScoreRing run={run} score={score} statusMain={statusMain} />

        <Box
          sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
          onClick={(e) => e.stopPropagation()}
        >
          {canTrain && (
            <Tooltip
              title={
                run.status === 3 ? t("common:retrain") : t("common:trainVerb")
              }
            >
              <IconButton size="small" onClick={() => onTrain(run)}>
                <PlayArrow fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          <Tooltip title={t("common:edit")}>
            <IconButton size="small" onClick={() => setConfigOpen(true)}>
              <Edit fontSize="small" />
            </IconButton>
          </Tooltip>
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

        {/* Wrapped so clicks inside the modal (a portal) don't bubble through
            the React tree into the card's onClick={onOpen} above */}
        <Box onClick={(e) => e.stopPropagation()}>
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

          <RunEditDialog
            run={run}
            session={session}
            existingRuns={existingRuns}
            onRefresh={onRefresh}
            open={configOpen}
            onClose={() => setConfigOpen(false)}
          />
        </Box>
      </Box>

      {/* Footer hint — signals the whole card is clickable to open the
          full model detail view (configuration, metrics, predictions, etc.) */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2.5,
          pt: 0.75,
          pb: 1.5,
        }}
      >
        <Typography
          variant="caption"
          color="text.disabled"
          sx={{
            fontSize: "0.6rem",
            fontWeight: 500,
            letterSpacing: 0.4,
            textTransform: "uppercase",
          }}
        >
          {t("models:label.metrics")} | {t("models:label.operations")}
        </Typography>
        <ChevronRight
          className="card-chevron-icon"
          sx={{
            fontSize: 16,
            color: "text.disabled",
            transition: "color 0.15s",
          }}
        />
      </Box>
    </Paper>
  );
}

ScoreRing.propTypes = {
  run: PropTypes.shape({
    status: PropTypes.number,
  }).isRequired,
  score: PropTypes.shape({
    score: PropTypes.number,
    breakdown: PropTypes.array,
  }),
  statusMain: PropTypes.string.isRequired,
};

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
  score: PropTypes.shape({
    score: PropTypes.number,
    breakdown: PropTypes.array,
  }),
  session: PropTypes.shape({
    id: PropTypes.number,
    name: PropTypes.string,
    task_name: PropTypes.string,
  }),
  existingRuns: PropTypes.array,
  onTrain: PropTypes.func.isRequired,
  onDelete: PropTypes.func.isRequired,
  onRefresh: PropTypes.func,
  onOpen: PropTypes.func.isRequired,
  isHighlighted: PropTypes.bool,
};

export default ModelCardCompact;
