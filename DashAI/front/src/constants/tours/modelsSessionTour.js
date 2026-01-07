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
        <p>
          You can see all your models in this session, compare their metrics,
          and decide which one works best for your data.
        </p>
      </div>
    ),
    placement: "center",
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
