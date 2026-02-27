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
          <p></p>
          <strong></strong>
        </div>
      </Trans>
    ),
    placement: "right",
    disableBeacon: true,
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
