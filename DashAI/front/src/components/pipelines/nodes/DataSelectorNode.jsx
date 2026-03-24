import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import DatasetModal from "../../../components/datasets/DatasetModal";
import { validateNode } from "../../../api/pipeline";
import { Button, Grid, Paper, Typography, LinearProgress } from "@mui/material";
import { AddCircleOutline as AddIcon } from "@mui/icons-material";
import { DataGrid } from "@mui/x-data-grid";
import { getDatasets } from "../../../api/datasets";
import { useSnackbar } from "notistack";

function DataSelectorNode({ onClose, onSave, savedConfig = null }) {
  const [datasetId, setDatasetId] = useState(savedConfig ? savedConfig.id : "");
  const [openModal, setOpenModal] = useState(false);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const { enqueueSnackbar } = useSnackbar();
  const [validationStatus, setValidationStatus] = useState("");

  const fetchDatasets = async () => {
    setLoading(true);
    const res = await getDatasets();
    setDatasets(res);
    setLoading(false);
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleDatasetUpdate = async (newDatasetId) => {
    await fetchDatasets();
    if (newDatasetId) {
      setDatasetId(newDatasetId);
    }
  };

  const handleOpenModal = () => setOpenModal(true);
  const handleCloseModal = () => setOpenModal(false);

  const handleSave = async () => {
    const selected = datasets.find((d) => d.id === datasetId);
    if (!selected) {
      console.error("Selected dataset not found.");
      return;
    }

    const config = {
      datasetName: selected.name,
      datasetPath: selected.file_path,
    };

    try {
      const response = await validateNode("DataSelector", config);
      if (response.status === "ok") {
        setValidationStatus("ok");
        onSave(selected);
        onClose();
      } else {
        setValidationStatus("error");
        enqueueSnackbar("Validation failed", { variant: "error" });
      }
    } catch (e) {
      setValidationStatus("error");
      enqueueSnackbar("Error validating node", { variant: "error" });
      console.error(e);
    }
  };

  const columns = [
    { field: "id", headerName: "ID", width: 80 },
    { field: "name", headerName: "Name", flex: 1 },
  ];

  return (
    <Paper sx={{ p: 3 }}>
      <Grid container spacing={2}>
        <Grid
          size={{ xs: 12 }}
          container
          justifyContent="space-between"
          alignItems="center"
        >
          <Typography variant="h6">Select a Dataset</Typography>
          <Button
            variant="contained"
            onClick={handleOpenModal}
            endIcon={<AddIcon />}
          >
            New Dataset
          </Button>
        </Grid>

        {openModal && (
          <DatasetModal
            open={openModal}
            setOpen={handleCloseModal}
            updateDatasets={handleDatasetUpdate}
          />
        )}

        <Grid size={{ xs: 12 }}>
          <div style={{ height: 300 }}>
            <DataGrid
              rows={datasets}
              columns={columns}
              loading={loading}
              onRowClick={(params) => setDatasetId(params.id)}
              rowSelectionModel={[datasetId]}
              pageSizeOptions={[5]}
              checkboxSelection={false}
              disableRowSelectionOnClick={false}
              slots={{
                loadingOverlay: LinearProgress,
              }}
            />
          </div>
        </Grid>

        <Grid size={{ xs: 12 }} container justifyContent="flex-end">
          <Button
            onClick={handleSave}
            disabled={!datasetId}
            variant="contained"
          >
            Save
          </Button>
        </Grid>
      </Grid>
    </Paper>
  );
}

DataSelectorNode.propTypes = {
  onClose: PropTypes.func.isRequired,
  onSave: PropTypes.func.isRequired,
  savedConfig: PropTypes.object,
};

export default DataSelectorNode;
