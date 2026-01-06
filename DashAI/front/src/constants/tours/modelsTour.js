import React from "react";

export const modelsTourSteps = [
  {
    target: "body",
    content: (
      <div>
        <h3>Models Module</h3>
        <p>
          Welcome to the Models section! This is where you manage your machine
          learning models, training sessions, and predictions.
        </p>
        <p>
          You can train models, compare their performance, and use them to make
          predictions on new data.
        </p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-left-panel"]',
    content: (
      <div>
        <h3>Sessions and Datasets Panel</h3>
        <p>
          On the left, you'll find all your training sessions organized by task.
        </p>
        <p>
          <strong>Sessions</strong> are where you train and compare different
          models for the same machine learning task.
        </p>
        <p>
          Each session is linked to a dataset and a specific task like
          Classification or Regression.
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-center-panel"]',
    content: (
      <div>
        <h3>Main Workspace</h3>
        <p>This is your main working area. Here you can:</p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            Select machine learning tasks (Classification, Regression, etc.)
          </li>
          <li>Create and configure training sessions</li>
          <li>Add models to your sessions</li>
          <li>View model performance and compare metrics</li>
        </ul>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-right-panel"]',
    content: (
      <div>
        <h3>Available Models</h3>
        <p>
          On the right side, you'll see all the machine learning models
          available for your selected task.
        </p>
        <p>
          Each model has different strengths and characteristics. You can click
          on any model to add it to your session and start training.
        </p>
        <p>
          <strong>Tip:</strong> Try adding multiple models to compare their
          performance!
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-task-selection"]',
    content: (
      <div>
        <h3>Select a Machine Learning Task</h3>
        <p>
          To create a session, first select what type of problem you want to
          solve.
        </p>
        <p>Common tasks include:</p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            <strong>Classification:</strong> Predict categories (e.g., spam or
            not spam)
          </li>
          <li>
            <strong>Regression:</strong> Predict continuous values (e.g., house
            prices)
          </li>
          <li>
            <strong>Time Series:</strong> Forecast future values over time
          </li>
        </ul>
        <p>
          <strong>Click on this task to continue the tour!</strong>
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
  },
  {
    target: '[data-tour="models-dataset-selection"]',
    content: (
      <div>
        <h3>Select a Dataset</h3>
        <p>
          Now you need to choose which dataset you want to use for training your
          models.
        </p>
        <p>
          The dataset contains the data that your models will learn from. Make
          sure it matches the task you selected.
        </p>
        <p>
          <strong>
            Click on the dropdown and select a dataset to continue!
          </strong>
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlay: true,
    isInteractive: true,
  },
];

export const modelsTourConfig = {
  continuous: true,
  showProgress: true,
  showBackButton: true,
  showSkipButton: true,
  disableOverlayClose: true,
  disableCloseOnEsc: false,
  locale: {
    back: "Back",
    close: "Close",
    last: "Finish",
    next: "Next",
    skip: "Skip Tour",
  },
};
