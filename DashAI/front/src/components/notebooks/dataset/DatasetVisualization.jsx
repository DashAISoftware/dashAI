import { useCallback, useState, useEffect } from "react";
import {
  Button,
  Grid,
  Paper,
  Typography,
  CircularProgress,
  Box,
  Chip,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import { getDatasetFile, getDatasetInfo } from "../../../api/datasets";
import { createNotebook } from "../../../api/notebook";
import DatasetTable from "../dataset/DatasetTable";
import { CreateNotebookModal } from "../notebookCreation/CreateNotebookModal";
import { useSnackbar } from "notistack";
import { useNavigate } from "react-router-dom";
import { getDatasetStatus } from "../../../utils/datasetStatus";

export default function DatasetVisualization({ dataset, onNotebookCreated }) {
  if (!dataset) {
    return (
      <Box
        sx={{ display: "flex", justifyContent: "center", alignItems: "center" }}
      >
        <CircularProgress sx={{ color: "#00BEBB" }} />
        <Typography>Loading...</Typography>
      </Box>
    );
  }

  const [showCreateNotebookModal, setShowCreateNotebookModal] = useState(false);
  const [datasetInfo, setDatasetInfo] = useState(null);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();

  // Format date for display
  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "numeric",
        hour12: true,
      });
    } catch (error) {
      return dateString;
    }
  };

  // Fetch dataset info when component mounts or dataset changes
  useEffect(() => {
    const fetchDatasetInfo = async () => {
      if (
        getDatasetStatus(dataset.status) === "Delivered" ||
        getDatasetStatus(dataset.status) === "Not Started" ||
        getDatasetStatus(dataset.status) === "Started"
      ) {
        return;
      }

      try {
        const info = await getDatasetInfo(dataset.id);
        setDatasetInfo(info);
      } catch (error) {
        console.error("Error fetching dataset info:", error);
        setDatasetInfo(null);
      }
    };

    fetchDatasetInfo();
  }, [dataset.id, dataset.status]);

  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      // Don't try to fetch data if it's a temporary/processing dataset
      if (
        getDatasetStatus(dataset.status) === "Delivered" ||
        getDatasetStatus(dataset.status) === "Not Started" ||
        getDatasetStatus(dataset.status) === "Started"
      ) {
        return { rows: [], total: 0 };
      }

      try {
        const data = await getDatasetFile(dataset.file_path, page, pageSize);
        return { rows: data.rows ?? [], total: data.total ?? 0 };
      } catch (error) {
        console.error("Error fetching dataset data:", error);
        return { rows: [], total: 0 };
      }
    },
    [dataset.file_path, dataset.status, dataset.id],
  );

  const handleCreateNotebook = async (notebookData) => {
    try {
      const notebookPayload = {
        name: notebookData.name,
        description: notebookData.description,
        dataset_id: dataset.id,
      };

      const createdNotebook = await createNotebook(notebookPayload);

      enqueueSnackbar("Notebook created successfully", {
        variant: "success",
      });

      setShowCreateNotebookModal(false);

      if (onNotebookCreated) {
        onNotebookCreated(createdNotebook);
      }
    } catch (error) {
      console.error("Error creating notebook:", error);
      enqueueSnackbar("Error creating notebook", {
        variant: "error",
      });
    }
  };

  const isProcessing =
    getDatasetStatus(dataset.status) === "Delivered" ||
    getDatasetStatus(dataset.status) === "Not Started" ||
    getDatasetStatus(dataset.status) === "Started";

  return (
    <>
      {/* Dataset Info Section */}
      {!isProcessing && datasetInfo && (
        <Paper
          sx={{
            bgcolor: "#212121",
            borderRadius: 2,
            boxShadow: "none",
            p: 2,
            mb: 2,
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
            <Typography variant="body2" color="text.secondary">
              Dataset Info:
            </Typography>
            <Chip
              label={`${datasetInfo.total_rows || 0} rows`}
              size="small"
              variant="outlined"
              sx={{ color: "text.primary", borderColor: "divider" }}
            />
            <Chip
              label={`${datasetInfo.total_columns || 0} columns`}
              size="small"
              variant="outlined"
              sx={{ color: "text.primary", borderColor: "divider" }}
            />
            {dataset.created && (
              <Chip
                label={`Created: ${formatDate(dataset.created)}`}
                size="small"
                variant="outlined"
                sx={{ color: "text.primary", borderColor: "divider" }}
              />
            )}
          </Box>
        </Paper>
      )}

      {/* Main Dataset Visualization */}
      <Paper
        sx={{
          bgcolor: "#212121",
          borderRadius: 2,
          boxShadow: "none",
          p: 2,
        }}
      >
        {/* Title and button */}
        <Grid
          container
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 4 }}
        >
          <Typography variant="h5" component="h2">
            {dataset.name}
          </Typography>
          <Grid item>
            <Button
              variant="contained"
              disabled={isProcessing}
              onClick={() => {
                navigate("../app/experiments", {
                  state: { dataset: dataset },
                });
              }}
              endIcon={<AddIcon />}
              sx={{ mr: 2 }}
            >
              New Experiment
            </Button>
            <Button
              variant="contained"
              endIcon={<AddIcon />}
              disabled={isProcessing}
              onClick={(e) => {
                e.stopPropagation();
                setShowCreateNotebookModal(true);
              }}
            >
              New Notebook
            </Button>
          </Grid>
        </Grid>

        {/* Table - only show if not processing */}
        {!isProcessing && (
          <DatasetTable
            fetchPage={fetchDatasetPage}
            deps={[dataset.file_path]}
            initialPageSize={10}
            datasetPath={dataset.file_path}
          />
        )}

        {/* Processing placeholder */}
        {isProcessing && (
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 200,
              flexDirection: "column",
              gap: 2,
            }}
          >
            <CircularProgress sx={{ color: "#00BEBB" }} />
            <Typography>Processing your dataset...</Typography>
            <Typography
              variant="body2"
              color="text.secondary"
              textAlign="center"
            >
              This may take a few moments depending on the size of your data.
            </Typography>
          </Box>
        )}

        <CreateNotebookModal
          open={showCreateNotebookModal}
          onClose={() => setShowCreateNotebookModal(false)}
          onCreateNotebook={handleCreateNotebook}
          dataset={dataset}
        />
      </Paper>
    </>
  );
}
