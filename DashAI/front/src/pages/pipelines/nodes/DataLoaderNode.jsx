import React, { useState, useEffect } from "react";
import DatasetModal from "../../../components/datasets/DatasetModal";
import { validateNode } from "../../../api/pipeline";
import { DialogActions, Button, Select, MenuItem, InputLabel, FormControl } from "@mui/material";
import { getDatasets } from "../../../api/datasets";

function DataLoaderNode({ onClose, onSave, savedConfig }) {
  const [datasetName, setDatasetName] = useState(savedConfig ? savedConfig.datasetName : "");
  const [openModal, setOpenModal] = useState(false);
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    const fetchDatasets = async () => {
      const res = await getDatasets();
      setDatasets(res);
    };

    fetchDatasets();
  }, []);

  const handleDatasetUpdate = async (newDatasetName) => {
    setDatasetName(newDatasetName);
  };

  const handleOpenModal = () => {
    setOpenModal(true);
  };

  const handleCloseModal = () => {
    setOpenModal(false);
  };

  const handleSave = async () => {
    const selected = datasets.find((d) => d.name === datasetName);
    if (!selected) {
      console.error("Selected dataset not found.");
      return;
    }

    const config = {
      datasetName: selected.name,
      datasetPath: selected.file_path,
    };

    const validationResponse = await validateNode("DataLoader", config);

    if (validationResponse.status === "ok") {
      console.log("Node validated successfully");
      const nodeData = {
        ...config,
        status: "ok"
      };
      onSave(nodeData);
      onClose();
    } else {
      console.error("Validation failed:", validationResponse.message);
    }
  };

  return (
    <div style={{ padding: "1rem", borderRadius: "0.5rem" }}>
      <div>
        <Button
          onClick={handleOpenModal}
          variant="contained"
          style={{ marginBottom: "2rem" }}
        >
          Upload Dataset
        </Button>

        {openModal && (
          <DatasetModal
            open={openModal}
            setOpen={handleCloseModal}
            updateDatasets={(newDatasetName) => {
              handleDatasetUpdate(newDatasetName);
              console.log("Dataset updated or added!");
            }}
          />
        )}

        <div>
          <FormControl fullWidth>
            <InputLabel id="dataset-select-label">Choose existing dataset</InputLabel>
            <Select
              labelId="dataset-select-label"
              id="dataset-select"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              label="Choose existing dataset"
            >
              <MenuItem value="">-- Select a dataset --</MenuItem>
              {datasets.map((dataset) => (
                <MenuItem key={dataset.id} value={dataset.name}>
                  {dataset.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </div>
      </div>

      <DialogActions>
        <Button onClick={handleSave} disabled={!datasetName} color="primary">
          Save
        </Button>
      </DialogActions>
    </div>
  );
}

export default DataLoaderNode;
