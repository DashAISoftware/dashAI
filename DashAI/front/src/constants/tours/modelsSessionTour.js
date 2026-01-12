import { maxWidth } from "@mui/system";
import React from "react";

export const modelsSessionTourSteps = [
  {
    target: "body",
    content: (
      <div>
        <h3>Session Visualization</h3>
        <p>
          Welcome to the Session Visualization! This is where you can compare
          different models, train them, and analyze their performance.
        </p>
        <p>Let's start by adding some models to compare in this session.</p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-right-panel"]',
    content: (
      <div>
        <h3>Available Models</h3>
        <p>
          On the right panel, you'll see all the machine learning models
          compatible with your selected task.
        </p>
        <p>
          Each model has different algorithms and approaches. Click on any model
          to add it to your session!
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
  },
  {
    target: '[data-tour="first-model"]',
    content: (
      <div>
        <h3>Add Your First Model</h3>
        <p>
          Click on this model to add it to your session. This will create a
          "run" that you can configure and train.
        </p>
        <p>
          <strong>Click on the model to continue!</strong>
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
  },
  {
    target: '[data-tour="model-config"]',
    content: (
      <div>
        <h3>Model Configuration</h3>
        <p>Here you can configure your model before training:</p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            <strong>Run Name:</strong> Give this run a meaningful name to
            identify it later
          </li>
          <li>
            <strong>Model Parameters:</strong> Configure the hyperparameters for
            your selected model
          </li>
        </ul>
        <p>
          Once you're happy with the configuration, click{" "}
          <strong>Add Model</strong> to add this model to your session.
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    disableScrolling: true,
    disableScrollParentFix: true,
    disableOverlay: true,
    spotlightClicks: true,
    isInteractive: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="first-run-card"]',
    content: (
      <div>
        <h3>Your Model Run Card</h3>
        <p>
          Perfect! This card contains everything about your model run. Here you
          can:
        </p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            <strong>Train:</strong> Start the training process with your
            configured parameters
          </li>
          <li>
            <strong>View Metrics:</strong> See performance scores once training
            is complete
          </li>
          <li>
            <strong>Make Predictions:</strong> Use your trained model on new
            data
          </li>
          <li>
            <strong>Create Explainers:</strong> Understand how your model makes
            decisions
          </li>
        </ul>
        <p>Let's train this model to see how it performs!</p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    disableScrolling: true,
    disableScrollParentFix: true,
  },
  {
    target: '[data-tour="train-button"]',
    content: (
      <div>
        <h3>Train Your Model</h3>
        <p>
          Click the <strong>Train</strong> button to start training your model
          with the configured parameters.
        </p>
        <p>
          The training process will run in the background, and you'll be able to
          see the progress and results here.
        </p>
        <p>
          <strong>Click "Train" to continue!</strong>
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
    target: '[data-tour="model-comparison-panel"]',
    content: (
      <div>
        <h3>Model Comparison</h3>
        <p>
          Once you have trained multiple models, this comparison panel will show
          you a side-by-side view of all your models' performance.
        </p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            <strong>Metrics Comparison:</strong> Compare accuracy, precision,
            recall, and other metrics
          </li>
          <li>
            <strong>Parameter Analysis:</strong> See which hyperparameters
            worked best
          </li>
          <li>
            <strong>Best Model:</strong> Quickly identify your top-performing
            model
          </li>
        </ul>
        <p>This makes it easy to choose the best model for your task!</p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
  },
  {
    target: '[data-tour="graphs-button"]',
    content: (
      <div>
        <h3>Visualize Results</h3>
        <p>
          Want to see your results in a more visual way? Click the{" "}
          <strong>Graphs</strong> button to switch from the table view to
          interactive charts.
        </p>
        <p>
          <strong>Click "Graphs" to continue!</strong>
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="model-comparison-panel"]',
    content: (
      <div>
        <h3>Performance Visualizations</h3>
        <p>
          The graphs view shows performance metrics, confusion matrices, and
          other visualizations to help you better understand your models'
          performance.
        </p>
        <p style={{ marginTop: "12px" }}>
          🎉 <strong>Great job!</strong> You can now add more models and
          experiment with different parameters!
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    disableScrolling: true,
    disableScrollParentFix: true,
    disableOverlay: true,
    spotlightClicks: true,
    maxWidth: "320px",
  },
];

export const modelsSessionTourConfig = {
  continuous: true,
  showProgress: true,
  showBackButton: true,
  showSkipButton: true,
  disableOverlayClose: true,
  disableCloseOnEsc: false,
  disableScrollParentFix: true,
  locale: {
    back: "Back",
    close: "Close",
    last: "Finish",
    next: "Next",
    skip: "Skip Tour",
  },
};
