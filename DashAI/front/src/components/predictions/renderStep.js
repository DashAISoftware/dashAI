import React from "react";
import SelectModelStep from "./SelectModelStep";
import SelectDatasetStep from "./SelectDatasetStep";

export const renderStep = (
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
  defaultName,
  selectedTaskName,
  setSelectedTaskName,
  forecastPeriods,
  setForecastPeriods,
) => {
  switch (stepName) {
    case "selectModel":
      return (
        <SelectModelStep
          defaultPredictionName={defaultName}
          selectedModelId={selectedModelId}
          setSelectedModelId={setSelectedModelId}
          setNextEnabled={setNextEnabled}
          onPredictNameInput={handlePredictNameInput}
          setTrainDataset={setTrainDataset}
          selectedTaskName={selectedTaskName}
          setSelectedTaskName={setSelectedTaskName}
        />
      );
    case "selectDataset":
      return (
        <SelectDatasetStep
          selectedModelId={selectedModelId}
          trainDataset={trainDataset}
          setSelectedDatasetId={setSelectedDatasetId}
          setNextEnabled={setNextEnabled}
          handlePredictNameInput={handlePredictNameInput}
          predictName={predictName}
          defaultName={defaultName}
          preselectedModelId={preselectedModelId}
          selectedTaskName={selectedTaskName}
          forecastPeriods={forecastPeriods}
          setForecastPeriods={setForecastPeriods}
        />
      );
    default:
      return null;
  }
};
