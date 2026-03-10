import { Trans } from "react-i18next";

export const datasetViewTourSteps = [
  {
    target: ".datasets-list",
    content: (
      <Trans i18nKey="datasetsTour:yourDatasets">
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
    disableScrolling: true,
    disableScrollParentFix: true,
  },
  {
    target: '[data-tour="datasets-new-notebook-button"]',
    content: (
      <Trans i18nKey="datasetsTour:nextSteps">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    spotlightClicks: true,
    disableOverlayClose: true,
    hideFooter: true,
    isInteractive: true,
  },
  {
    target: ".notebook-note-box",
    content: (
      <Trans i18nKey="datasetsTour:importantNote">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    disableBeacon: true,
    disableOverlayClose: true,
    disableCloseOnEsc: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="create-notebook-button"]',
    content: (
      <Trans i18nKey="datasetsTour:finishProcess">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "top",
    spotlightClicks: true,
    disableOverlayClose: true,
    disableBeacon: true,
    isInteractive: true,
  },
];

export const datasetViewTourConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: true,
  disableOverlayClose: true,
  disableCloseOnEsc: false,
  scrollToFirstStep: false,
};
