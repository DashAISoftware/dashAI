import { homeTourSteps, homeTourConfig } from "./homeTour";
import { datasetsTourSteps, datasetsTourConfig } from "./datasetsTour";
import { datasetViewTourSteps, datasetViewTourConfig } from "./datasetViewTour";
import { notebookTourSteps, notebookTourConfig } from "./notebookTour";
import { experimentsTourSteps, experimentsTourConfig } from "./experimentsTour";
import { modelsTourSteps, modelsTourConfig } from "./modelsTour";
import {
  modelsSessionTourSteps,
  modelsSessionTourConfig,
} from "./modelsSessionTour";
import { generativeTourSteps, generativeTourConfig } from "./generativeTour";

export const tours = {
  home: {
    steps: homeTourSteps,
    config: homeTourConfig,
  },
  datasets: {
    steps: datasetsTourSteps,
    config: datasetsTourConfig,
  },
  datasetView: {
    steps: datasetViewTourSteps,
    config: datasetViewTourConfig,
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
  generative: {
    steps: generativeTourSteps,
    config: generativeTourConfig,
  },
};

export const TOUR_KEYS = {
  HOME: "home",
  DATASETS: "datasets",
  DATASET_VIEW: "datasetView",
  NOTEBOOK: "notebook",
  EXPERIMENTS: "experiments",
  MODELS: "models",
  MODELS_SESSION: "modelsSession",
  PREDICTIONS: "predictions",
  EXPLAINABILITY: "explainability",
  PIPELINES: "pipelines",
  GENERATIVE: "generative",
};
