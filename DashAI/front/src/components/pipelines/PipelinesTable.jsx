import React, { useState, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
} from "@mui/icons-material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";

import { getPipelines, deletePipeline } from "../../api/pipeline";
import { formatDate } from "../../utils";
import { Visibility as ViewIcon } from "@mui/icons-material";
import { GridActionsCellItem } from "@mui/x-data-grid";
import { useNavigate } from "react-router-dom";
import DeleteItemModal from "../../components/custom/DeleteItemModal";

function PipelinesTable({
  handleOpenNewPipeline,
  updateTableFlag,
  setUpdateTableFlag,
}) {
  const [loading, setLoading] = useState(true);
  const [pipelines, setPipelines] = useState([]);
  const { enqueueSnackbar } = useSnackbar();
  const navigate = useNavigate();

  const fetchPipelines = async () => {
    setLoading(true);
    try {
      const data = await getPipelines();
      setPipelines(data);
    } catch (error) {
      enqueueSnackbar("Error while fetching pipelines", { variant: "error" });
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPipelines();
  }, []);

  useEffect(() => {
    if (updateTableFlag) {
      setUpdateTableFlag(false);
      fetchPipelines();
    }
  }, [updateTableFlag]);

  const handleDelete = async (id) => {
    try {
      await deletePipeline(id);
      enqueueSnackbar("Pipeline deleted successfully", { variant: "success" });
      fetchPipelines();
    } catch (error) {
      enqueueSnackbar("Failed to delete pipeline", { variant: "error" });
      console.error(error);
    }
  };

  const columns = useMemo(
    () => [
      {
        field: "name",
        headerName: "Name",
        minWidth: 250,
        editable: false,
      },
      {
        field: "created",
        headerName: "Created",
        minWidth: 150,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "last_modified",
        headerName: "Edited",
        minWidth: 150,
        valueGetter: (value) => formatDate(value),
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 160,
        getActions: (params) => [
          <GridActionsCellItem
            key="view"
            icon={<ViewIcon />}
            label="View"
            onClick={() => navigate(`/app/pipelines/${params.id}`)}
          />,
          <DeleteItemModal
            key="delete-button"
            deleteFromTable={() => handleDelete(params.id)}
          />,
        ],
      },
    ],
    [],
  );

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      <Grid
        container
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="h5">Current Pipelines</Typography>
        <Grid>
          <Grid container spacing={2}>
            <Grid>
              <Button
                variant="contained"
                onClick={() => navigate("/app/pipelines/new")}
                endIcon={<AddIcon />}
              >
                New Pipeline
              </Button>
            </Grid>
            <Grid>
              <Button
                variant="contained"
                onClick={fetchPipelines}
                endIcon={<UpdateIcon />}
              >
                Update
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      <DataGrid
        rows={pipelines}
        columns={columns}
        initialState={{
          pagination: {
            paginationModel: { pageSize: 5 },
          },
        }}
        sortModel={[{ field: "last_modified", sort: "desc" }]}
        autoHeight
        pageSizeOptions={[5, 10]}
        disableRowSelectionOnClick
        loading={loading}
        slots={{
          toolbar: GridToolbar,
          loadingOverlay: LinearProgress,
        }}
      />
    </Paper>
  );
}

PipelinesTable.propTypes = {
  handleOpenNewPipeline: PropTypes.func,
  updateTableFlag: PropTypes.bool.isRequired,
  setUpdateTableFlag: PropTypes.func.isRequired,
};

export default PipelinesTable;
