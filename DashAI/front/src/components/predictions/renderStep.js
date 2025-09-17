import React from "react";
import SelectModelStep from "./SelectModelStep";
import SelectDatasetStep from "./SelectDatasetStep";

export function renderStep(
  stepName,
  preselectedModelId,
  setSelectedModelId,
  setSelectedDatasetId,
  setNextEnabled,
  handlePredictNameInput,
  setTrainDataset,
  trainDataset,
) {
  switch (stepName) {
    case "selectModel":
      return (
        <SelectModelStep
          setSelectedModelId={setSelectedModelId}
          setNextEnabled={setNextEnabled}
          onPredictNameInput={handlePredictNameInput}
          setTrainDataset={setTrainDataset}
        />
      );
    case "selectDataset":
      return (
        <SelectDatasetStep
          preselectedModelId={preselectedModelId}
          handlePredictNameInput={handlePredictNameInput}
          setSelectedDatasetId={setSelectedDatasetId}
          setNextEnabled={setNextEnabled}
          trainDataset={trainDataset}
        />
      );
    default:
      return null;
  }
}
