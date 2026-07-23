import React, { useState, useCallback, useEffect } from "react";
import PropTypes from "prop-types";
import {
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Box,
  Tooltip,
  Button,
  Collapse,
  CircularProgress,
} from "@mui/material";
import DeleteConfirmationModal from "../threeSectionLayout/DeleteConfirmationModal";
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  Dataset as DatasetIcon,
} from "@mui/icons-material";
import { getPredictionStatus } from "../../utils/predictionStatus";
import { deletePrediction } from "../../api/predict";
import { useSnackbar } from "notistack";
import DatasetTable from "../notebooks/dataset/DatasetTable";
import {
  getDatasetFile,
  getDatasetFileFiltered,
  exportDatasetCsvByPath,
  getDatasetTypesByFilePath,
} from "../../api/datasets";
import { useTheme } from "@mui/material/styles";
import { useTranslation } from "react-i18next";

import {
  getTargetDecimals,
  formatPredictionRows,
} from "../../utils/predictionFormat";

const RUNNING_STATUSES = [1, 2]; // Delivered or Started

/**
 * PredictionCard - Displays a single prediction with results table
 */
export default function PredictionCard({
  prediction,
  onDelete,
  onUpdate,
  targetColumn = null,
  datasetSample = null,
}) {
  const [expanded, setExpanded] = useState(() => {
    const saved = localStorage.getItem(`prediction-${prediction.id}-expanded`);
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [columnTypes, setColumnTypes] = useState({});
  const theme = useTheme();
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "datasets", "common"]);

  // Persist expanded state
  useEffect(() => {
    localStorage.setItem(
      `prediction-${prediction.id}-expanded`,
      JSON.stringify(expanded),
    );
  }, [expanded, prediction.id]);

  // Fetch column types when results path changes
  useEffect(() => {
    if (!prediction?.results_path) return;
    getDatasetTypesByFilePath(prediction.results_path)
      .then(setColumnTypes)
      .catch(() => {});
  }, [prediction?.results_path]);

  const statusText = prediction.status;

  // Status color mapping
  const getStatusColor = (status) => {
    switch (status) {
      case 0: // Not Started
        return "default";
      case 1: // Delivered
      case 2: // Started
        return "info";
      case 3: // Finished
        return "success";
      case 4: // Error
        return "error";
      default:
        return "default";
    }
  };

  const isRunning = RUNNING_STATUSES.includes(statusText);
  const isFinished = statusText === 3; // Finished

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString();
  };

  const handleDelete = async () => {
    try {
      await deletePrediction(prediction.id);
      enqueueSnackbar(t("prediction:message.deletedSuccessfully"), {
        variant: "success",
      });
      setDeleteDialogOpen(false);
      if (onDelete) onDelete();
    } catch (error) {
      console.error("Error deleting prediction:", error);
      enqueueSnackbar(t("prediction:error.errorDeleting"), {
        variant: "error",
      });
    }
  };

  const handleDownload = async () => {
    try {
      const blob = await exportDatasetCsvByPath(prediction.results_path);
      const isZip = blob.type === "application/zip";
      const ext = isZip ? "zip" : "csv";
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `prediction-${prediction.id}-${
          new Date(prediction.created).toISOString().split("T")[0]
        }.${ext}`,
      );
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      enqueueSnackbar(t("prediction:message.downloadedSuccessfully"), {
        variant: "success",
      });
    } catch (error) {
      console.error("Error downloading prediction:", error);
      enqueueSnackbar(t("prediction:error.errorDownloading"), {
        variant: "error",
      });
    }
  };

  const fetchPage = useCallback(
    async (page, pageSize, filterModel, sortModel) => {
      if (!prediction.results_path) return { rows: [], total: 0 };
      const hasFilters =
        filterModel?.items?.length > 0 || (sortModel && sortModel.length > 0);
      const data = hasFilters
        ? await getDatasetFileFiltered(
            prediction.results_path,
            page,
            pageSize,
            filterModel,
            sortModel,
          )
        : await getDatasetFile(prediction.results_path, page, pageSize);
      const targetDecimals = getTargetDecimals(datasetSample, targetColumn);
      return {
        rows: formatPredictionRows(
          data.rows ?? [],
          targetColumn,
          targetDecimals,
        ),
        total: data.total ?? 0,
      };
    },
    [prediction.results_path, datasetSample, targetColumn],
  );

  return (
    <>
      <Card elevation={2} sx={{ width: "100%", maxWidth: 900 }}>
        <CardContent sx={{ pb: 2 }}>
          {/* Header with status and dataset info */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "start",
              mb: 2,
            }}
          >
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2" fontWeight="medium">
                {t("prediction:label.prediction")} #{prediction.id}
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                {formatDate(prediction.created)}
              </Typography>
              {prediction.dataset_id && (
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    gap: 1,
                    mt: 1,
                  }}
                >
                  <DatasetIcon
                    fontSize="small"
                    color="action"
                    sx={{ fontSize: "0.875rem" }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {prediction.dataset?.name ||
                      t("datasets:label.unknownDataset")}
                  </Typography>
                </Box>
              )}
            </Box>
            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
              <Chip
                label={getPredictionStatus(statusText, t)}
                color={getStatusColor(statusText)}
                size="small"
              />
              <Tooltip title={t("prediction:button.downloadResults")}>
                <span>
                  <IconButton
                    size="small"
                    disabled={!isFinished}
                    color="primary"
                    onClick={handleDownload}
                  >
                    <DownloadIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title={t("common:delete")}>
                <span>
                  <IconButton
                    size="small"
                    onClick={() => setDeleteDialogOpen(true)}
                    disabled={isRunning}
                    color="error"
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </span>
              </Tooltip>
            </Box>
          </Box>

          {/* Expandable Results */}
          {isFinished && (
            <Box sx={{ mt: 4 }}>
              <Button
                size="small"
                onClick={() => setExpanded(!expanded)}
                endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                sx={{ textTransform: "none" }}
              >
                {expanded
                  ? t("prediction:button.hideResults")
                  : t("prediction:button.showResults")}
              </Button>

              <Collapse in={expanded} timeout="auto" unmountOnExit>
                <Box sx={{ mt: 4 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mb: 2, display: "block" }}
                  >
                    {t("prediction:label.resultsPreview")}
                  </Typography>
                  <Box
                    sx={{
                      border: 1,
                      borderColor: "divider",
                      bgcolor: "background.default",
                      borderRadius: 1,
                      overflow: "hidden",
                      p: 1,
                    }}
                  >
                    <DatasetTable
                      fetchPage={fetchPage}
                      initialPageSize={10}
                      datasetPath={prediction.results_path}
                      columnTypes={columnTypes}
                      showExportButton={false}
                      baseBackgroundColor={theme.palette.background.paper}
                      showBorder={false}
                    />
                  </Box>
                </Box>
              </Collapse>
            </Box>
          )}

          {/* Show loading indicator if prediction is running */}
          {isRunning && (
            <Box
              sx={{
                py: 4,
                textAlign: "center",
                color: "text.secondary",
              }}
            >
              <CircularProgress size={24} />
              <Typography variant="body2" sx={{ mt: 2 }}>
                {t("prediction:label.predictionInProgress")}
              </Typography>
            </Box>
          )}
        </CardContent>
      </Card>

      <DeleteConfirmationModal
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        onConfirm={handleDelete}
        content={t("prediction:label.confirmDeletion")}
      />
    </>
  );
}

PredictionCard.propTypes = {
  prediction: PropTypes.shape({
    id: PropTypes.number.isRequired,
    status: PropTypes.number.isRequired,
    created: PropTypes.string,
    dataset_id: PropTypes.number,
    dataset: PropTypes.shape({
      name: PropTypes.string,
    }),
    results_path: PropTypes.string,
  }).isRequired,
  onDelete: PropTypes.func,
  onUpdate: PropTypes.func,
};
