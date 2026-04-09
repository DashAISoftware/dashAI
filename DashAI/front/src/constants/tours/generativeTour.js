import { Trans } from "react-i18next";

export const generativeTourSteps = [
  {
    target: "body",
    content: (
      <Trans i18nKey="generativeTour:generativeModule">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="task-gallery"]',
    content: (
      <Trans i18nKey="generativeTour:taskGallery">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "right",
    disableBeacon: true,
    maxWidth: "320px",
  },
  {
    target: '[data-tour="task-selection"]',
    content: (
      <Trans i18nKey="generativeTour:taskCard">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
  },

  {
    target: '[data-tour="model-card-qwen"]',
    content: (
      <Trans i18nKey="generativeTour:selectModel">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
    disableBackButton: true,
    maxWidth: "320px",
  },

  {
    target: '[data-tour="model-parameters"]',
    content: (
      <Trans i18nKey="generativeTour:modelParameters">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
  },
  {
    target: '[data-tour="create-session-button"]',
    content: (
      <Trans i18nKey="generativeTour:createSession">
        <div>
          <h3></h3>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
  },
  {
    target: '[data-tour="sessions-left-panel"]',
    content: (
      <Trans i18nKey="generativeTour:sessionsPanel">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "right",
    disableBeacon: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="parameters-right-panel"]',
    content: (
      <Trans i18nKey="generativeTour:parametersPanel">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    isInteractive: true,
  },
  {
    target: '[data-tour="chat-input"]',
    content: (
      <Trans i18nKey="generativeTour:sendMessage">
        <div>
          <h3></h3>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    placement: "top",
    disableBeacon: true,
    disableOverlay: true,
    spotlightClicks: true,
    isInteractive: true,
  },
];

export const generativeTourConfig = {
  continuous: true,
  showProgress: true,
  showBackButton: true,
  showSkipButton: true,
  disableOverlayClose: true,
  disableCloseOnEsc: false,
};
