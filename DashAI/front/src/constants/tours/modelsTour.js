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
    disableBackButton: true,
  },
  {
    target: '[data-tour="models-next-button"]',
    content: (
      <div>
        <h3>Continue to Dataset Configuration</h3>
        <p>
          Great! Now that you've selected your dataset, click the{" "}
          <strong>Next</strong> button to proceed to the dataset configuration
          step.
        </p>
        <p>
          In the next step, you'll be able to select which columns to use as
          inputs and outputs for your model training.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="models-validation-alert"]',
    content: (
      <div>
        <h3>Column Validation</h3>
        <p>
          This alert shows whether your selected input and output columns match
          the requirements of your chosen task.
        </p>
        <p>
          <strong>Green (Success):</strong> Your columns are correctly
          configured and ready for training.
        </p>
        <p>
          <strong>Red (Error):</strong> The columns don't match the task
          requirements. You'll need to adjust your selection.
        </p>
        <p>
          The alert explains what types and how many columns are needed for
          inputs and outputs.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="dataset-input-columns-autocomplete"]',
    content: (
      <div>
        <h3>Input Columns</h3>
        <p>
          Here you select which columns from your dataset will be used as{" "}
          <strong>features</strong> (inputs) for training your model.
        </p>
        <p>
          Input columns contain the information the model will analyze to make
          predictions. For example:
        </p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            In a house price prediction: square footage, bedrooms, location
          </li>
          <li>In spam detection: email text, sender, subject line</li>
        </ul>
        <p>
          You can select multiple columns. By default, all columns except the
          last one are selected as inputs.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
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
