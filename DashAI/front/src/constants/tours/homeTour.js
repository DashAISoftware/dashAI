import { Trans } from "react-i18next";

export const homeTourSteps = [
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <Trans i18nKey={"homeTour:datasetsIntro"}>
        <div>
          <h3></h3>
          <p></p>
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
          <h3></h3>
          <p></p>
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
          <h3></h3>
          <p></p>
          <div style={{ marginTop: "10px" }}></div>
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
          <h3></h3>
          <p></p>
          <div style={{ marginTop: "10px" }}></div>
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
