export const homeTourSteps = [
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <div>
        <h3>Datasets</h3>
        <p>
          Here you upload, manage, and explore your datasets. This is the
          natural starting point of any project.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
  },
  {
    target: '[data-tour="models-button"]',
    content: (
      <div>
        <h3>Models</h3>
        <p>
          In this module you can train, compare, and use your models to make
          predictions, monitoring metrics such as Accuracy, F1, Recall, and
          Precision.
        </p>
      </div>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="explainability-button"]',
    content: (
      <div>
        <h3>Explainability</h3>
        <p>
          Here you interpret the model and identify the variables that most
          influence its decisions.
        </p>
        <div style={{ marginTop: "10px" }}>
          📊 Understand what drives your model's predictions
        </div>
      </div>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="pipelines-button"]',
    content: (
      <div>
        <h3>Pipelines</h3>
        <p>
          This lets you chain preprocessing, training, and evaluation steps into
          a reproducible workflow.
        </p>
        <div style={{ marginTop: "10px" }}>🔗 Build automated ML workflows</div>
      </div>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <div>
        <h3>Ready to Start!</h3>
        <p>
          Remember that <strong>Datasets</strong> is the natural starting point
          of the workflow. Next, we'll move on to the Datasets section.
        </p>
      </div>
    ),
    placement: "bottom",
    styles: {
      spotlight: {
        borderRadius: "8px",
      },
    },
  },
];

export const homeTourConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: true,
  disableOverlayClose: false,
  disableCloseOnEsc: false,
  locale: {
    back: "Back",
    close: "Close",
    last: "Finish",
    next: "Next",
    skip: "Skip Tour",
  },
};
