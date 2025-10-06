import { homeTourSteps, homeTourConfig } from './homeTour';
// import { datasetsTourSteps, datasetsTourConfig } from './datasetsTour';

export const tours = {
  home: {
    steps: homeTourSteps,
    config: homeTourConfig,
  },
  // datasets: {
  //   steps: datasetsTourSteps,
  //   config: datasetsTourConfig,
  // },
};

export const TOUR_KEYS = {
  HOME: 'home',
  DATASETS: 'datasets',
  EXPERIMENTS: 'experiments',
  PREDICTIONS: 'predictions',
  EXPLAINABILITY: 'explainability',
  PIPELINES: 'pipelines',
};