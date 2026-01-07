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
          Each model has different algorithms and approaches. Let's add a few to
          compare which one works best!
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
    hideFooter: true,
  },
  {
    target: '[data-tour="run-cards-section"]',
    content: (
      <div>
        <h3>Your First Run</h3>
        <p>
          Great! Your model has been added as a "run". Each run represents one
          model configured for your task.
        </p>
        <p>
          You can see the model's configuration here. Later, you'll be able to
          train it and view its performance metrics.
        </p>
        <p>
          <strong>Let's add one more model to compare!</strong>
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
  },
  {
    target: '[data-tour="models-right-panel"]',
    content: (
      <div>
        <h3>Add Another Model</h3>
        <p>Now click on a different model from the list to add a second one.</p>
        <p>
          Having multiple models allows you to compare their performance and
          choose the best one for your data.
        </p>
        <p>
          <strong>Click on any other model to continue!</strong>
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="model-comparison-panel"]',
    content: (
      <div>
        <h3>Model Comparison Panel</h3>
        <p>
          Perfect! Now you have multiple models to compare. This panel shows all
          your models side-by-side.
        </p>
        <p>
          The panel stays at the top as you scroll, so you can always see the
          comparison while reviewing individual model details below.
        </p>
        <p>
          You can switch between <strong>Table view</strong> to compare specific
          metrics, or <strong>Graph view</strong> to visualize performance
          trends.
        </p>
      </div>
    ),
    placement: "bottom",
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
  locale: {
    back: "Back",
    close: "Close",
    last: "Finish",
    next: "Next",
    skip: "Skip Tour",
  },
};
