import React, { useState, useCallback } from "react";
import PropTypes from "prop-types";
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  IconButton,
  Chip,
  Box,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
  Collapse,
  CircularProgress,
} from "@mui/material";
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
import { getDatasetFile, exportDatasetCsvByPath } from "../../api/datasets";
import { useTranslation } from "react-i18next";

const RUNNING_STATUSES = [1, 2]; // Delivered or Started

/**
 * PredictionCard - Displays a single prediction with results table
 */
export default function PredictionCard({ prediction, onDelete, onUpdate }) {
  const [expanded, setExpanded] = useState(true);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const { enqueueSnackbar } = useSnackbar();
  const { t } = useTranslation(["prediction", "datasets", "common"]);

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
      const data = await exportDatasetCsvByPath(prediction.results_path);
      const blob = new Blob([data], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `prediction-${prediction.id}-${
          new Date(prediction.created).toISOString().split("T")[0]
        }.csv`,
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
    async (page, pageSize) => {
      if (!prediction.results_path) return { rows: [], total: 0 };
      const data = await getDatasetFile(
        prediction.results_path,
        page,
        pageSize,
      );
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [prediction.results_path],
  );

  return (
    <>
      <Card elevation={2} sx={{ width: "100%" }}>
        <CardContent sx={{ pb: 1 }}>
          {/* Header with status and dataset info */}
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "start",
              mb: 1,
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
                    gap: 0.5,
                    mt: 0.5,
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
            <Chip
              label={getPredictionStatus(statusText, t)}
              color={getStatusColor(statusText)}
              size="small"
            />
          </Box>

          {/* Expandable Results */}
          {isFinished && (
            <Box sx={{ mt: 2 }}>
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
                <Box sx={{ mt: 2 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ mb: 1, display: "block" }}
                  >
                    {t("prediction:label.resultsPreview")}
                  </Typography>
                  <DatasetTable
                    fetchPage={fetchPage}
                    initialPageSize={100}
                    autoHeight={true}
                    slots={{ toolbar: null }}
                    datasetPath={prediction.results_path}
                    hideFooter={true}
                    pageSizeOptions={[]}
                    sx={{
                      maxHeight: 400,
                      width: "100%",
                      "& .MuiDataGrid-columnHeaders": {
                        backgroundColor: "background.box",
                      },
                    }}
                  />
                </Box>
              </Collapse>
            </Box>
          )}

          {/* Show loading indicator if prediction is running */}
          {isRunning && (
            <Box
              sx={{
                py: 2,
                textAlign: "center",
                color: "text.secondary",
              }}
            >
              <CircularProgress size={24} />
              <Typography variant="body2" sx={{ mt: 1 }}>
                {t("prediction:label.predictionInProgress")}
              </Typography>
            </Box>
          )}
        </CardContent>

        <CardActions sx={{ justifyContent: "flex-end", pt: 0 }}>
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
        </CardActions>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>{t("prediction:label.confirmDeletionTitle")}</DialogTitle>
        <DialogContent>
          <DialogContentText>
            {t("prediction:label.confirmDeletion")}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>
            {t("common:cancel")}
          </Button>
          <Button onClick={handleDelete} color="error" autoFocus>
            {t("common:delete")}
          </Button>
        </DialogActions>
      </Dialog>
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
