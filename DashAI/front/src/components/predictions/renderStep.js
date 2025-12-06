import React from "react";
import SelectModelStep from "./SelectModelStep";
import SelectDatasetStep from "./SelectDatasetStep";

export function renderStep(
  stepName,
  selectedModelId,
  preselectedModelId,
  setSelectedModelId,
  setSelectedDatasetId,
  setNextEnabled,
  handlePredictNameInput,
  setTrainDataset,
  trainDataset,
  predictName,
  defaultPredictionName,
  manualInputData,
  setManualInputData,
) {
  switch (stepName) {
    case "selectModel":
      return (
        <SelectModelStep
          setSelectedModelId={setSelectedModelId}
          setNextEnabled={setNextEnabled}
          onPredictNameInput={handlePredictNameInput}
          setTrainDataset={setTrainDataset}
          defaultPredictionName={defaultPredictionName}
        />
      );
    case "selectDataset":
      return (
        <SelectDatasetStep
          selectedModelId={selectedModelId}
          preselectedModelId={preselectedModelId}
          handlePredictNameInput={handlePredictNameInput}
          setSelectedDatasetId={setSelectedDatasetId}
          setNextEnabled={setNextEnabled}
          defaultPredictionName={defaultPredictionName}
          trainDataset={trainDataset}
          predictName={predictName}
          onPredictNameInput={handlePredictNameInput}
          manualInputData={manualInputData}
          setManualInputData={setManualInputData}
        />
      );
    default:
      return null;
  }
}
