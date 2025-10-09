import { homeTourSteps, homeTourConfig } from './homeTour';
import { datasetsTourSteps, datasetsTourConfig } from './datasetsTour';
import { notebookTourSteps, notebookTourConfig } from './notebookTour';

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
  }
};

export const TOUR_KEYS = {
  HOME: 'home',
  DATASETS: 'datasets',
  NOTEBOOK: 'notebook',
  EXPERIMENTS: 'experiments',
  PREDICTIONS: 'predictions',
  EXPLAINABILITY: 'explainability',
  PIPELINES: 'pipelines',
};