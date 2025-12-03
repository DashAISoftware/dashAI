import React, { useEffect } from "react";
import { getRunById } from "../../api/run";
import { getExperimentById } from "../../api/experiment";
import { getDatasetTypes, getDatasetSample } from "../../api/datasets";

import { Box } from "@mui/system";
import ManualInputForm from "./ManualInputForm";

export default function ManualInput({
  runId,
  manualInputData,
  setManualInputData,
}) {
  const [experiment, setExperiment] = React.useState(null);
  const [types, setTypes] = React.useState({});
  const [loading, setLoading] = React.useState(true);
  const [sample, setSample] = React.useState(null);

  useEffect(() => {
    const fetchExperiment = async () => {
      setLoading(true);
      try {
        const run = await getRunById(runId);
        if (run && run.experiment_id) {
          const experimentData = await getExperimentById(run.experiment_id);
          setExperiment(experimentData);
          const datasetTypes = await getDatasetTypes(experimentData.dataset_id);
          setTypes(datasetTypes);
          const datasetSample = await getDatasetSample(
            experimentData.dataset_id,
          );
          setSample(datasetSample);
        }
      } catch (error) {
        console.error("Error fetching experiment:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchExperiment();
  }, [runId]);

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
