import React, { useState, useEffect, useRef, useMemo } from "react";
import PropTypes from "prop-types";
import { Button, Grid, Paper, Typography } from "@mui/material";
import { MaterialReactTable, useMaterialReactTable } from "material-react-table";
import { MRT_Localization_ES } from "material-react-table/locales/es";
import { MRT_Localization_EN } from "material-react-table/locales/en";
import { useTheme } from "@mui/material/styles";
import { filterModels } from "../../../api/pipeline";
import { useSnackbar } from "notistack";
import { validateNode } from "../../../api/pipeline";
import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

function RetrieveModelNode({
  onClose,
  onSave,
  savedConfig = null,
  prevNodes = [],
}) {
  const datasetNode = prevNodes?.find((node) => node?.file_path && node?.id);
  const datasetId = datasetNode?.id ?? null;
  const [pipelines, setPipelines] = useState([]);
  const [selectedModelId, setSelectedModelId] = useState(null);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const { pipelineId } = useParams();
  const hasWarnedRef = useRef(false);
  const { i18n } = useTranslation();
  const theme = useTheme();
  const localization = i18n.language.startsWith("es")
    ? MRT_Localization_ES
    : MRT_Localization_EN;

  useEffect(() => {
    if (savedConfig?.model_path && pipelines.length > 0) {
      const matching = pipelines.find(
        (p) => p.train?.model_path === savedConfig.model_path,
      );
      if (matching) {
        setSelectedModelId(matching.id);
      }
    }
  }, [savedConfig, pipelines]);

  useEffect(() => {
    const fetchCompatibleModels = async () => {
      if (!datasetId) {
        if (!hasWarnedRef.current) {
          enqueueSnackbar("Missing dataset", { variant: "warning" });
          hasWarnedRef.current = true;
        }
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

  const columns = useMemo(
    () => [
      { accessorKey: "id", header: "ID", size: 80 },
      { accessorKey: "name", header: "Name", grow: true },
      {
        id: "model",
        header: "Model",
        grow: true,
        accessorFn: (row) => row.train?.info || "Unknown",
      },
    ],
    [],
  );

  const table = useMaterialReactTable({
    columns,
    data: pipelines,
    state: { isLoading: loading },
    getRowId: (row) => String(row.id),
    enableRowSelection: false,
    muiTableBodyRowProps: ({ row }) => ({
      onClick: () => setSelectedModelId(row.original.id),
      sx: {
        cursor: "pointer",
        backgroundColor:
          row.original.id === selectedModelId
            ? theme.palette.action.selected
            : undefined,
      },
    }),
    enablePagination: true,
    initialState: { pagination: { pageSize: 5, pageIndex: 0 } },
    localization,
    enableFullScreenToggle: false,
    enableDensityToggle: false,
  });

  return (
    <Paper sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12 }}>
          <Typography variant="h6">Select a trained model</Typography>
          <Typography variant="body2" color="textSecondary">
            Choose a trained model from one of the saved pipelines to use in
            this node.
          </Typography>
        </Grid>

        <Grid size={{ xs: 12 }}>
          <div style={{ height: 300, overflow: "auto" }}>
            <MaterialReactTable table={table} />
          </div>
        </Grid>

        <Grid size={{ xs: 12 }} container justifyContent="flex-end">
          <Button
            onClick={handleSave}
            disabled={!selectedModelId}
            variant="contained"
          >
            Save
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
}

RetrieveModelNode.propTypes = {
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
  prevNodes: PropTypes.arrayOf(PropTypes.object),
};

export default RetrieveModelNode;
