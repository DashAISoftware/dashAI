import { Trans } from "react-i18next";

export const notebookTourSteps = [
  {
    target: "body",
    content: (
      <Trans i18nKey="notebookTour:notebookIntro">
        <div>
          <h3></h3>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="dataset-preview-section"]',
    content: (
      <Trans i18nKey="notebookTour:datasetPreview">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "bottom",
    disableBeacon: true,
  },
  {
    target: ".right-bar-container",
    content: (
      <Trans i18nKey="notebookTour:explorersPanel">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
          <p>
            <strong></strong>
          </p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
  },
  {
    target: '[data-tour="histogram-explorer"]',
    content: (
      <Trans i18nKey="notebookTour:histogramExplorer">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="column-selector-explorer-container"]',
    content: (
      <Trans i18nKey="notebookTour:selectColumns">
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
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="explorer-parameters"]',
    content: (
      <Trans i18nKey="notebookTour:configureParameters">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    disableBeacon: true,
    spotlightClicks: true,
  },
  {
    target: '[data-tour="create-explorer-button"]',
    content: (
      <Trans i18nKey="notebookTour:createExplorer">
        <div>
          <h3></h3>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlayClose: true,
    disableOverlay: true,
    hideFooter: true,
  },
  {
    target: ".explorer-box",
    content: (
      <Trans i18nKey="notebookTour:explorerCreated">
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
    placement: "left",
    disableBeacon: true,
  },
  {
    target: '[data-tour="converters-tab"]',
    content: (
      <Trans i18nKey="notebookTour:convertersTab">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="label-encoder-converter"]',
    content: (
      <Trans i18nKey="notebookTour:labelEncoderConverter">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="column-selector-converter-container"]',
    content: (
      <Trans i18nKey="notebookTour:selectColumnsEncode">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <ul>
            <li>
              <strong></strong>
            </li>
            <li>
              <strong></strong>
            </li>
          </ul>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlay: true,
    hideFooter: true,
  },
  {
    target: ".converter-box",
    content: (
      <Trans i18nKey="notebookTour:converterApplied">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
  },
  {
    target: '[data-tour="nan-remover-converter"]',
    content: (
      <Trans i18nKey="notebookTour:nanRemoverConverter">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <p></p>
        </div>
      </Trans>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="column-selector-converter-container"]',
    content: (
      <Trans i18nKey="notebookTour:selectColumnsClean">
        <div>
          <h3></h3>
          <p></p>
          <p>
            <strong></strong>
          </p>
        </div>
      </Trans>
    ),
    disableBeacon: true,
    spotlightClicks: true,
    disableOverlay: true,
    hideFooter: true,
  },

  {
    target: ".save-dataset-button",
    content: (
      <Trans i18nKey="notebookTour:saveProcessedDataset">
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
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },
  {
    target: '[data-tour="save-dataset-modal-notebook"]',
    content: (
      <Trans i18nKey="notebookTour:finalStep">
        <div>
          <h3></h3>
          <p></p>
          <p></p>
          <hr style={{ margin: "15px 0", borderTop: "1px solid #ddd" }} />
          <h4></h4>
          <p></p>
          <ul style={{ marginBottom: "15px" }}>
            <li></li>
            <li></li>
            <li></li>
          </ul>
          <div
            style={{
              backgroundColor: "#f0f9ff",
              border: "1px solid #bae6fd",
              borderRadius: "4px",
              padding: "8px 12px",
              marginTop: "15px",
            }}
          >
            <p style={{ margin: "0", fontWeight: "bold" }}></p>
          </div>
        </div>
      </Trans>
    ),
    disableBeacon: true,
    spotlightClicks: true,
    disableScrolling: true,
    disableOverlayClose: true,
    showSkipButton: false,
    hideBackButton: false,
    styles: {
      options: {
        zIndex: 2000,
      },
      buttonNext: {
        backgroundColor: "#1976d2",
      },
      buttonBack: {
        color: "#1976d2",
      },
    },
    locale: {
      last: "Finish Tour",
      next: "Finish Tour",
    },
  },
];

export const notebookTourConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: true,
  disableOverlayClose: false,
  disableCloseOnEsc: false,
};
