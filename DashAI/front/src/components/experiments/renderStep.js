import React from "react";
import SetNameAndTaskStep from "./SetNameAndTaskStep";
import SelectDatasetStep from "./SelectDatasetStep";
import PrepareDatasetStep from "./PrepareDatasetStep";
import ConfigureModelsStep from "./ConfigureModelsStep";
import HyperparameterOptimizationStep from "./HyperparameterOptimizationStep";
import MetricsSelector from "./metrics/MetricsSelector";

export function renderStep(
  stepName,
  newExp,
  setNewExp,
  setNextEnabled,
  defaultName,
  existingExperiments,
) {
  switch (stepName) {
    case "selectTask":
      return (
        <SetNameAndTaskStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
          defaultExperimentName={defaultName}
          existingExperiments={existingExperiments}
        />
      );
    case "selectDataset":
      return (
        <SelectDatasetStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
        />
      );
    case "prepareDataset":
      return (
        <PrepareDatasetStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
        />
      );
    case "metricsSelection":
      return (
        <MetricsSelector
          experiment={newExp}
          setExperiment={setNewExp}
          setNextEnabled={setNextEnabled}
        />
      );
    case "configureModels":
      return (
        <ConfigureModelsStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
        />
      );
    case "configureOptimizer":
      return (
        <HyperparameterOptimizationStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
        />
      );
    default:
      return null;
  }
}
