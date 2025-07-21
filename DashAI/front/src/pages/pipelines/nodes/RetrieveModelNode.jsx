import React, { useState, useEffect } from "react";
import {
  Button,
  Grid,
  Paper,
  Typography,
  LinearProgress,
} from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { filterModels } from "../../../api/pipeline";
import { useSnackbar } from "notistack";
import { validateNode } from "../../../api/pipeline";
import { useParams } from "react-router-dom";

function RetrieveModelNode({ onClose, onSave, savedConfig, prevNodes }) {
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const [pipelines, setPipelines] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const { pipelineId } = useParams();

  useEffect(() => {
    if (savedConfig?.model_path && pipelines.length > 0) {
        const matching = pipelines.find(p => p.train?.model_path === savedConfig.model_path);
        if (matching) {
        setSelectedModelId(matching.id);
        }
    }
  }, [savedConfig, pipelines]);

  useEffect(() => {
    const fetchCompatibleModels = async () => {
        if (!datasetId) {
        enqueueSnackbar("Missing dataset", { variant: "warning" });
        setLoading(false);
        return;
        }

        setLoading(true);
        try {
        const result = await filterModels(datasetId, pipelineId);
        setPipelines(result);
        } catch (error) {
        enqueueSnackbar("Error retrieving models", { variant: "error" });
        } finally {
        setLoading(false);
        }
    };

    fetchCompatibleModels();
    }, [datasetId, enqueueSnackbar]);

  const handleSave = async () => {
    const selected = pipelines.find((m) => m.id === selectedModelId);
    if (!selected) return;

    const train = selected.train || {};
    const nodeData = {
        model: train.info || "",
        model_path: train.model_path || "",
        input_columns: train.input_columns || [],
        task: train.task || "",
    };

    try {
        const response = await validateNode("RetrieveModel", nodeData);
        if (response.status === "ok") {
          onSave(nodeData);
          onClose();
        } else {
          enqueueSnackbar("Validation failed", { variant: "error" });
        }
    } catch (e) {
        enqueueSnackbar("Error validating node", { variant: "error" });
        console.error(e);
    }
  };

  const columns = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "name", headerName: "Name", flex: 1 },
    {
        field: "model",
        headerName: "Model",
        flex: 1,
        valueGetter: (params) => params.row.train?.info || "Unknown"
    },
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <Typography variant="h6">Select a trained model</Typography>
          <Typography variant="body2" color="textSecondary">
            Choose a trained model from one of the saved pipelines to use in this node.
          </Typography>
        </Grid>

        <Grid item xs={12}>
          <div style={{ height: 300 }}>
            <DataGrid
              rows={pipelines}
              columns={columns}
              loading={loading}
              onRowClick={(params) => setSelectedModelId(params.id)}
              selectionModel={selectedModelId ? [selectedModelId] : []}
              pageSizeOptions={[5]}
              checkboxSelection={false}
              disableRowSelectionOnClick={false}
              slots={{
                loadingOverlay: LinearProgress,
              }}
            />
          </div>
        </Grid>

        <Grid item xs={12} container justifyContent="flex-end">
          <Button onClick={handleSave} disabled={!selectedModelId} variant="contained">
            Save
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
}

export default RetrieveModelNode;
