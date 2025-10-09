import React from 'react';

export const datasetsTourSteps = [
  {
    target: 'body',
    content: (
      <div>
        <h3>Dataset Module</h3>
        <p>
          This is where you manage your data and create interactive notebooks for analysis.
          Let's see how to get started!
        </p>
      </div>
    ),
    placement: 'center',
    disableBeacon: true,
  },
  {
    target: '[data-tour="dataset-option"]',
    content: (
      <div>
        <h3>Upload Dataset</h3>
        <p>
          This is where you import your own files from various formats and sources.
        </p>
        <p>
          You can upload CSV, Excel, and other common data formats.
        </p>
      </div>
    ),
    placement: 'bottom',
  },
  {
    target: '[data-tour="notebook-option"]',
    content: (
      <div>
        <h3>Create Notebook</h3>
        <p>
          This lets you explore or transform datasets interactively.
        </p>
        <p>
          Notebooks are where you visualize data, apply transformations, and prepare it for modeling.
        </p>
      </div>
    ),
    placement: 'bottom',
  },
  {
    target: '[data-tour="sample-option"]',
    content: (
      <div>
        <h3>Load Sample Dataset</h3>
        <p>
          If you don't have any data yet, you can quickly start by loading DashAI's sample dataset.
        </p>
        <div style={{ marginTop: '10px', fontWeight: 'bold', color: '#1976d2' }}>
          Click "Upload Sample Dataset" to continue!
        </div>
      </div>
    ),
    placement: 'bottom',
    spotlightClicks: true,
    disableBeacon: true,
    hideFooter:true,
  },
  {
    target: '.datasets-list',
    content: (
      <div>
        <h3>Your Datasets</h3>
        <p>
          The Personality dataset is now available in your Datasets list.
        </p>
        <p>
          You can find all your uploaded datasets and notebooks in this sidebar.
        </p>
      </div>
    ),
    placement: 'right',
  },
  {
    target: '.new-notebook-button',
    content: (
      <div>
        <h3>Next Steps: Create a Notebook</h3>
        <p>
          Now click "New Notebook" to open the dataset in an interactive environment.
        </p>
        <p>
          In a notebook, you can analyze, visualize, and transform your data.
        </p>
      </div>
    ),
    placement: 'bottom',
    spotlightClicks: true,
    disableOverlayClose: true,
    hideFooter:true, 
  },
 {
    target: '.notebook-note-box',
    content: (
      <div>
        <h3>Important Note</h3>
        <p>
          Pay attention to this information
        </p>
        <p>
          This ensures your original data remains intact while you experiment.
        </p>
      </div>
    ),
    placement: 'bottom',
    disableBeacon: true,
    disableOverlayClose: true,
    disableCloseOnEsc: true,
  },
  {
    target: '[data-tour="create-notebook-button"]',
    content: (
      <div>
        <h3>Finish the Process</h3>
        <p>
          Click "Create Notebook" to start working with your data in an interactive environment.
        </p>
        <p>
          You'll be able to visualize, transform, and prepare your data for modeling.
        </p>
      </div>
    ),
    placement: 'bottom',
    spotlightClicks: true,
    disableOverlayClose: true,
    disableBeacon: true,
  }
];

export const datasetsTourConfig = {
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