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
        <p
          style={{
            backgroundColor: "#e8f5e9",
            padding: "8px",
            borderRadius: "4px",
            marginTop: "10px",
          }}
        >
          💡 <strong>Pro tip:</strong> The default parameters work well for most
          cases, but you can fine-tune them for better performance!
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
  },
  {
    target: '[data-tour="first-run-card"]',
    content: (
      <div>
        <h3>Your Model Run</h3>
        <p>
          Great! Your model has been added. This card shows all the information
          about your model run:
        </p>
        <ul style={{ marginLeft: "20px", lineHeight: "1.6" }}>
          <li>
            <strong>Status:</strong> Whether the model is trained, training, or
            not started
          </li>
          <li>
            <strong>Configuration:</strong> The parameters you selected
          </li>
          <li>
            <strong>Actions:</strong> Train, edit, or delete the model
          </li>
        </ul>
        <p>Let's train this model to see how it performs!</p>
      </div>
    ),
    placement: "bottom",
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
    placement: "top",
    disableBeacon: true,
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
