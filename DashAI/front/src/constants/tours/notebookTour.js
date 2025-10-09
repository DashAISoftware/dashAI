import React from 'react';

export const notebookTourSteps = [
  {
    target: 'body',
    content: (
      <div>
        <h3>Notebook Interface</h3>
        <p>
          Welcome to the Notebook! This is where you can explore, visualize, and transform your data.
          Let's discover how to use this interface effectively.
        </p>
      </div>
    ),
    placement: 'center',
    disableBeacon: true,
  },
  {
    target: '.dataset-preview-section',
    content: (
      <div>
        <h3>Dataset Preview</h3>
        <p>
          This section shows a preview of your dataset. You can see sample data and basic information.
        </p>
        <p>
          Remember that you're working with a copy of the original dataset, so any changes you make here won't affect the source data.
        </p>
      </div>
    ),
    placement: 'bottom',
    disableBeacon: true,
  },
 {
    target: '.explorer-converter-box',
    content: (
      <div>
        <h3>Explorers and Converters</h3>
        <p>
          In the notebook area below the dataset preview, you can add:
        </p>
        <p>
          <strong>Explorers</strong> - Visualizations like charts and statistics to understand your data
        </p>
        <p>
          <strong>Converters</strong> - Transformations to clean, filter, or modify your data
        </p>
      </div>
    ),
    placement: 'right',
    disableBeacon: true,
  },
  {
    target: '.save-dataset-button',
    content: (
      <div>
        <h3>Save as New Dataset</h3>
        <p>
          When you're satisfied with your data transformations, you can save the result as a new dataset.
        </p>
        <p>
          This creates a snapshot of your data at its current state, which you can use for modeling or further analysis.
        </p>
      </div>
    ),
    placement: 'top',
    disableBeacon: true,
  },
];

export const notebookTourConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: true,
  disableOverlayClose: false,
  disableCloseOnEsc: false,
  locale: {
    back: 'Back',
    close: 'Close',
    last: 'Finish',
    next: 'Next',
    skip: 'Skip Tour',
  },
};