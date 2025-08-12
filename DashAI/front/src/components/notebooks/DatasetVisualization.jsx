import { useCallback } from "react";
import { Button, Grid, Paper, Typography } from "@mui/material";
import { AddCircleOutline as AddIcon, Dataset } from "@mui/icons-material";
import { getDatasetFile } from "../../api/datasets";
import DatasetTable from "./DatasetTable";

export default function DatasetVisualization({ dataset }) {
  const fetchDatasetPage = useCallback(
    async (page, pageSize) => {
      const data = await getDatasetFile(dataset.file_path, page, pageSize);
      return { rows: data.rows ?? [], total: data.total ?? 0 };
    },
    [dataset.file_path],
  );

  return (
    <Paper sx={{ py: 4, px: 6 }}>
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
          <Button variant="contained" endIcon={<AddIcon />}>
            New Dataset
          </Button>
        </Grid>
      </Grid>

      {/* Table */}
      <DatasetTable
        fetchPage={fetchDatasetPage}
        deps={[dataset.file_path]}
        initialPageSize={5}
      />
    </Paper>
  );
}
