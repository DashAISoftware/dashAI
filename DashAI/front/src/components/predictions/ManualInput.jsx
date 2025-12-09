import React, { useEffect } from "react";
import { getRunById } from "../../api/run";
import { getExperimentById } from "../../api/experiment";
import { getDatasetTypes, getDatasetSample } from "../../api/datasets";

import { Box } from "@mui/system";
import ManualInputForm from "./ManualInputForm";

export default function ManualInput({
  experiment,
  loading,
  types,
  sample,
  manualInputData,
  setManualInputData,
}) {
  return (
    <Box sx={{ p: 2, border: "1px solid #ccc", borderRadius: 1 }}>
      {loading ? (
        <div>Loading...</div>
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
