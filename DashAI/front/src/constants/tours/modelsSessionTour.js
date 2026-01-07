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
