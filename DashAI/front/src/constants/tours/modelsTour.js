import { maxWidth } from "@mui/system";
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
          On the left, you'll find all your available datasets, and above them,
          all your training sessions organized by task.
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
        <p>
          This is your main working area. The content here changes depending on
          what you're doing.
        </p>
        <p>
          Right now, you can select a machine learning task to start creating a
          new session. Once you have sessions, you'll be able to add models,
          view their performance, and compare metrics here.
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="models-right-panel"]',
    content: (
      <div>
        <h3>Models Panel</h3>
        <p>
          This panel will display all machine learning models compatible with
          the task you select.
        </p>
        <p>
          Once you create your session, you'll be able to add and train
          different models here to compare which one works best with your data.
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
        </ul>
        <p>
          <strong>Click on this task to continue the tour!</strong>
        </p>
      </div>
    ),
    placement: "right",
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
    maxWidth: "320px",
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
          <strong style={{ color: "#2e7d32" }}>Green (Success):</strong> Your
          columns are correctly configured and ready for training.
        </p>
        <p>
          <strong style={{ color: "#d32f2f" }}>Red (Error):</strong> The columns
          don't match the task requirements. Don't worry! You can adjust your
          column selection in the next steps to fix this.
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
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlay: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="dataset-output-columns-autocomplete"]',
    content: (
      <div>
        <h3>Output Columns</h3>
        <p>
          Here you select which columns represent what the model should{" "}
          <strong>predict</strong> (the target or label).
        </p>
        <p>
          Output columns are what you want the model to learn to predict based
          on the input columns. For example:
        </p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>In house price prediction: the price column</li>
          <li>In spam detection: the spam/not spam label</li>
          <li>In customer churn: whether a customer will leave or stay</li>
        </ul>
        <p>
          Usually, you select one column as output. By default, the last column
          is selected.
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlay: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="exp-dataset-splits"]',
    content: (
      <div>
        <h3>Dataset Splits</h3>
        <p>
          Here you configure how to divide your dataset into different sets for
          training and evaluation.
        </p>
        <p>
          <strong>Training Set:</strong> Used to train the model (typically
          60-80%)
        </p>
        <p>
          <strong>Validation Set:</strong> Used to tune and validate during
          training (typically 10-20%)
        </p>
        <p>
          <strong>Test Set:</strong> Used to evaluate final model performance
          (typically 10-20%)
        </p>
        <p>
          You can choose between <strong>Random</strong> (automatic split),{" "}
          <strong>Manual</strong> (specify rows), or <strong>Predefined</strong>{" "}
          (if your dataset already has splits).
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="models-next-button"]',
    content: (
      <div>
        <h3>Create Your Session!</h3>
        <p>
          Once you've configured the input columns, output columns, and dataset
          splits, you're ready to create your training session!
        </p>
        <p>
          Click the <strong>Create Session</strong> button to finalize the setup
          and start adding machine learning models to train.
        </p>
        <p>
          <strong>Note:</strong> The button will only be enabled when all
          required configurations are valid (green validation alert).
        </p>
        <p style={{ marginTop: "10px", fontSize: "0.9em", color: "#666" }}>
          🎉 After creating the session, you'll be able to add different models
          from the right panel and compare their performance!
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
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
