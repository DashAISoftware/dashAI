import { homeTourSteps, homeTourConfig } from "./homeTour";
import { datasetsTourSteps, datasetsTourConfig } from "./datasetsTour";
import { notebookTourSteps, notebookTourConfig } from "./notebookTour";
import { experimentsTourSteps, experimentsTourConfig } from "./experimentsTour";
import { modelsTourSteps, modelsTourConfig } from "./modelsTour";
import {
  modelsSessionTourSteps,
  modelsSessionTourConfig,
} from "./modelsSessionTour";

export const tours = {
  home: {
    steps: homeTourSteps,
    config: homeTourConfig,
  },
  datasets: {
    steps: datasetsTourSteps,
    config: datasetsTourConfig,
  },
  notebook: {
    steps: notebookTourSteps,
    config: notebookTourConfig,
  },
  experiments: {
    steps: experimentsTourSteps,
    config: experimentsTourConfig,
  },
  models: {
    steps: modelsTourSteps,
    config: modelsTourConfig,
  },
  modelsSession: {
    steps: modelsSessionTourSteps,
    config: modelsSessionTourConfig,
  },
};

export const TOUR_KEYS = {
  HOME: "home",
  DATASETS: "datasets",
  NOTEBOOK: "notebook",
  EXPERIMENTS: "experiments",
  MODELS: "models",
  MODELS_SESSION: "modelsSession",
  PREDICTIONS: "predictions",
  EXPLAINABILITY: "explainability",
  PIPELINES: "pipelines",
};
