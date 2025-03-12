import React, { useState } from "react";
import DatasetModal from "../../../components/datasets/DatasetModal";

function DataLoaderNode({ open, onClose, onSave }) {
  const [datasetName, setDatasetName] = useState("");

  const handleDatasetUpdate = (newDatasetName) => {
    setDatasetName(newDatasetName);
    onSave({ datasetName: newDatasetName });
    onClose();
  };

  const handleOpenModal = () => {
    setOpen(true);
  };

  return (
    <div>
      <button onClick={handleOpenModal}>
        {datasetName ? "Change Dataset" : "Upload Dataset"}
      </button>

      {datasetName && <p>Dataset: {datasetName}</p>}

      <DatasetModal
        open={open}
        setOpen={onClose}
        updateDatasets={(newDatasetName) => {
          handleDatasetUpdate(newDatasetName);
          console.log("Dataset updated or added!");
        }}
      />
    </div>
  );
}

export default DataLoaderNode;
