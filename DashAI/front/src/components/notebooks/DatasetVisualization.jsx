import { useCallback } from "react";
import {
  Button,
  Grid,
  Paper,
  Typography,
  CircularProgress,
  Box,
} from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import { getDatasetFile } from "../../api/datasets";
import DatasetTable from "./DatasetTable";

export default function DatasetVisualization({ dataset }) {
  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      // Don't try to fetch data if it's a temporary/processing dataset
      if (
        dataset.status === "processing" ||
        dataset.id.toString().startsWith("temp_")
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

  // Check if dataset is still processing
  const isProcessing =
    dataset.status === "processing" ||
    dataset.id.toString().startsWith("temp_");

  return (
    <Paper
      sx={{
        bgcolor: "#212121",
        borderRadius: 2,
        boxShadow: "none",
        py: 4,
        px: 6,
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
            endIcon={<AddIcon />}
            disabled={isProcessing}
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
          initialPageSize={5}
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
          <CircularProgress size={60} />
          <Typography variant="h6" color="text.secondary">
            Processing your dataset...
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center">
            This may take a few moments depending on the size of your data.
          </Typography>
        </Box>
      )}
    </Paper>
  );
}
