import React, { useEffect, useState, useCallback } from "react";
import { DataGrid, GridActionsCellItem, GridToolbar } from "@mui/x-data-grid";
import { useSnackbar } from "notistack";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import {
  get_metadata_prediction_json,
  delete_prediction as deletePredictionRequest,
} from "../../api/predict";
import {
  AddCircleOutline as AddIcon,
  Update as UpdateIcon,
} from "@mui/icons-material";
import DeleteItemModal from "../custom/DeleteItemModal";
import EditPredictionModal from "./EditPredictionModal";
import PredictionSummaryModal from "./PredictionSummaryModal";
import DownloadPrediction from "./DownloadPrediction";

function PredictionTable({
  handleNewPredict,
  updateTableFlag,
  setUpdateTableFlag,
}) {
  const { enqueueSnackbar } = useSnackbar();
  const [loading, setLoading] = useState(true);
  const [models, setModels] = useState([]);

  const getModels = useCallback(async () => {
    setLoading(true);
    try {
      const uniqueModels = await get_metadata_prediction_json();
      setModels(uniqueModels);
    } catch (error) {
      enqueueSnackbar("Error when trying to get the predictions", {
        variant: "error",
      });
      console.error("Error fetching predictions:", error);
    } finally {
      setLoading(false);
    }
  }, [enqueueSnackbar]);

  const deletePrediction = async (predict_name) => {
    try {
      await deletePredictionRequest(predict_name);
      setUpdateTableFlag(true);
      enqueueSnackbar("Prediction successfully deleted.", {
        variant: "success",
      });
    } catch (error) {
      enqueueSnackbar("Error when trying to delete the prediction", {
        variant: "error",
      });
      console.error("Error deleting prediction:", error);
    }
  };

  const createDeleteHandler = useCallback(
    (predict_name) => () => {
      deletePrediction(predict_name);
    },
    [deletePrediction],
  );

  useEffect(() => {
    getModels();
  }, [getModels]);

  useEffect(() => {
    if (updateTableFlag) {
      getModels();
      setUpdateTableFlag(false);
    }
  }, [updateTableFlag, setUpdateTableFlag, getModels]);

  const columns = React.useMemo(
    () => [
      {
        field: "id",
        headerName: "ID",
        minWidth: 30,
        editable: false,
      },
      {
        field: "pred_name",
        headerName: "Prediction Name",
        minWidth: 200,
        editable: false,
      },
      {
        field: "dataset_name",
        headerName: "Dataset Name",
        minWidth: 200,
        editable: false,
      },
      {
        field: "model_name",
        headerName: "Model Name",
        minWidth: 200,
        editable: false,
      },
      {
        field: "run_name",
        headerName: "Model",
        minWidth: 150,
        editable: false,
      },
      {
        field: "task_name",
        headerName: "Task",
        minWidth: 150,
        editable: false,
      },
      {
        field: "actions",
        type: "actions",
        minWidth: 150,
        getActions: (params) => [
          <EditPredictionModal
            key="edit-component"
            predictName={params.row.pred_name}
            updatePredictions={() => setUpdateTableFlag(true)}
          />,
          <DeleteItemModal
            key="delete-component"
            deleteFromTable={createDeleteHandler(params.row.pred_name)}
          />,
          <PredictionSummaryModal
            key="summary-component"
            predictName={params.row.pred_name}
          />,
          <DownloadPrediction
            key="download-component"
            predictName={params.row.pred_name}
          />,
        ],
      },
    ],
    [createDeleteHandler, setUpdateTableFlag],
  );

  return (
    <Paper sx={{ py: 4, px: 6 }}>
      <Grid
        container
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ mb: 4 }}
      >
        <Typography variant="h5" component="h2">
          Current predicted datasets
        </Typography>
        <Grid item>
          <Grid container spacing={2}>
            <Grid item>
              <Button
                variant="contained"
                onClick={handleNewPredict}
                endIcon={<AddIcon />}
              >
                New Prediction
              </Button>
            </Grid>
            <Grid item>
              <Button
                variant="contained"
                onClick={() => setUpdateTableFlag(true)}
                endIcon={<UpdateIcon />}
                disabled={loading}
              >
                Update
              </Button>
            </Grid>
          </Grid>
        </Grid>
      </Grid>

      <div style={{ width: "100%", position: "relative" }}>
        <DataGrid
          rows={models}
          columns={columns}
          initialstate={{
            pagination: {
              paginationmodel: {
                pagesize: 5,
              },
            },
          }}
          getRowId={(row) => row.id}
          pageSize={5}
          sortModel={[{ field: "id", sort: "asc" }]}
          pageSizeOptions={[5, 10]}
          disableRowSelectionOnClick
          autoHeight
          loading={loading}
          slots={{
            toolbar: GridToolbar,
            loadingOverlay: LinearProgress,
          }}
          sx={{
            "& .MuiDataGrid-cell:focus": {
              outline: "none",
            },
          }}
        />
      </div>
    </Paper>
  );
}

export default PredictionTable;
