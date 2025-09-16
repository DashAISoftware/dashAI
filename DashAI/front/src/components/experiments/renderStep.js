import React from "react";
import SetNameAndTaskStep from "./SetNameAndTaskStep";
import SelectDatasetStep from "./SelectDatasetStep";
import PrepareDatasetStep from "./PrepareDatasetStep";
import ConfigureModelsStep from "./ConfigureModelsStep";
import HyperparameterOptimizationStep from "./HyperparameterOptimizationStep";

export function renderStep(stepName, newExp, setNewExp, setNextEnabled) {
  switch (stepName) {
    case "selectTask":
      return (
        <SetNameAndTaskStep
          newExp={newExp}
          setNewExp={setNewExp}
          setNextEnabled={setNextEnabled}
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
