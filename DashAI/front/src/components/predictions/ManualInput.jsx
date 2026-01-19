import React, { useEffect } from "react";
import { getRunById } from "../../api/run";
import { getModelSessionById } from "../../api/modelSession";
import { getDatasetTypes, getDatasetSample } from "../../api/datasets";

import { Box } from "@mui/system";
import ManualInputForm from "./ManualInputForm";
import { CircularProgress } from "@mui/material";

export default function ManualInput({
  experiment,
  loading,
  types,
  sample,
  manualInputData,
  setManualInputData,
}) {
  return (
    <Box>
      {loading ? (
        <CircularProgress />
      ) : experiment && Object.keys(types).length > 0 && sample ? (
        <ManualInputForm
          types={types}
          sample={sample}
          inputColumns={experiment.input_columns}
          onSubmit={(values) => console.log("Form submitted:", values)}
          manualInputData={manualInputData}
          setManualInputData={setManualInputData}
        />
      ) : (
        <div>No experiment data available.</div>
      )}
    </Box>
  );
}
