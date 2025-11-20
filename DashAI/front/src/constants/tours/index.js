import { homeTourSteps, homeTourConfig } from "./homeTour";
import { datasetsTourSteps, datasetsTourConfig } from "./datasetsTour";
import { notebookTourSteps, notebookTourConfig } from "./notebookTour";
import { experimentsTourSteps, experimentsTourConfig } from "./experimentsTour";

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
};

export const TOUR_KEYS = {
  HOME: "home",
  DATASETS: "datasets",
  NOTEBOOK: "notebook",
  EXPERIMENTS: "experiments",
  PREDICTIONS: "predictions",
  EXPLAINABILITY: "explainability",
  PIPELINES: "pipelines",
};
