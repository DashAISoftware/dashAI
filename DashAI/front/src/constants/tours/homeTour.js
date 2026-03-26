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
    target: '[data-tour="models-button"]',
    content: (
      <Trans i18nKey={"homeTour:modelsIntro"}>
        <div>
          <h3></h3>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="datasets-button"]',
    content: (
      <Trans i18nKey="homeTour:readyToStart">
        <div>
          <h3></h3>
          <p>
            <strong></strong>
          </p>
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
  disableOverlayClose: true,
  disableCloseOnEsc: false,
};
