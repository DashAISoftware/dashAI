import { Trans } from "react-i18next";

export const homeTourSteps = [
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <Trans i18nKey={"homeTour:datasetsIntro"}>
        <div>
          <h3>Datasets</h3>
          <p>
            Here you upload, manage, and explore your datasets. This is the
            natural starting point of any project.
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
  },
  {
    target: '[data-tour="experiments-button"]',
    content: (
      <Trans i18nKey={"homeTour:experimentsIntro"}>
        <div>
          <h3>Experiments</h3>
          <p>
            In this module you train and compare models, monitoring metrics such
            as Accuracy, F1, Recall, and Precision.
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="explainability-button"]',
    content: (
      <Trans i18nKey={"homeTour:explainabilityIntro"}>
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
      </Trans>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="pipelines-button"]',
    content: (
      <Trans i18nKey={"homeTour:pipelinesIntro"}>
        <div>
          <h3>Pipelines</h3>
          <p>
            This lets you chain preprocessing, training, and evaluation steps
            into a reproducible workflow.
          </p>
          <div style={{ marginTop: "10px" }}>
            🔗 Build automated ML workflows
          </div>
        </div>
      </Trans>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <Trans
        i18nKey="homeTour:readyToStart"
        components={{ strong: <strong /> }}
      >
        <div>
          <h3></h3>
          <p></p>
        </div>
      </Trans>
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
};
