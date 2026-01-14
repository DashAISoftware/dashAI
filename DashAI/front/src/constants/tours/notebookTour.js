import { Trans } from "react-i18next";

export const notebookTourSteps = [
  {
    target: "body",
    content: (
      <Trans i18nKey="notebookTour:notebookIntro">
        <div>
          <h3>Notebook Interface</h3>
          <p>
            Welcome to the Notebook! This is where you can explore, visualize,
            and transform your data. Let's discover how to use this interface
            effectively.
          </p>
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
          <h3>Dataset Preview</h3>
          <p>
            This section shows a preview of your dataset. You can see sample
            data and basic information.
          </p>
          <p>
            Remember that you're working with a copy of the original dataset, so
            any changes you make here won't affect the source data.
          </p>
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
          <h3>Explorers and Converters Panel</h3>
          <p>
            On the right side, you'll find the tools to analyze and transform
            your data.
          </p>
          <p>
            <strong>Explorers</strong> help you visualize data through charts
            and statistics.
          </p>
          <p>
            <strong>Converters</strong> allow you to transform, clean, and
            prepare your data.
          </p>
          <p>
            The Explorers tab is already selected. Let's create a histogram!
          </p>
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
          <h3>Histogram Plot Explorer</h3>
          <p>
            The Histogram Plot shows the distribution of values in your dataset.
          </p>
          <p>Click on "Histogram Plot" to add it to your notebook.</p>
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
          <h3>Configure Parameters</h3>
          <p>
            Here you can customize the explorer's parameters, such as the number
            of bins for the histogram.
          </p>
          <p>
            For now, we'll use the default settings. These work well for most
            cases!
          </p>
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
          <h3>Create the Explorer</h3>
          <p>
            Now click the "Create Explorer" button to generate the histogram
            visualization.
          </p>
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
          <h3>Explorer Created!</h3>
          <p>Great! Your histogram explorer is now processing.</p>
          <p>
            Once it's finished, you'll see the visualization here. Explorers
            help you understand your data's patterns and distributions.
          </p>
          <p>
            <strong>Now let's add a data transformation!</strong>
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
          <h3>Converters Tab</h3>
          <p>
            Click on the "Converters" tab to see available transformation tools.
          </p>
          <p>
            We'll use a Label Encoder to convert categorical data into numerical
            values.
          </p>
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
          <h3>Label Encoder Converter</h3>
          <p>
            Label Encoder transforms categorical text values into numerical
            codes.
          </p>
          <p>This is useful for preparing data for machine learning models!</p>
          <p>Click on "Label Encoder" to add it.</p>
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
          <h3>Select Columns to Encode</h3>
          <p>
            Select the categorical columns you want to convert into numerical
            values.
          </p>
          <p>For this example, try selecting columns like:</p>
          <ul>
            <li>
              <strong>stage_fear</strong>
            </li>
            <li>
              <strong>drained_after_socializing</strong>
            </li>
          </ul>
          <p>
            <strong>
              Click "Save" to apply the Label Encoder transformation.
            </strong>
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
          <h3>Converter Applied!</h3>
          <p>
            Excellent! Your Label Encoder is now processing the selected
            columns.
          </p>
          <p>
            Once finished, you'll see the transformation details here. All
            subsequent explorers and converters will use this transformed data.
          </p>
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
          <h3>NaN Remover Converter</h3>
          <p>
            The NaN Remover helps clean your dataset by removing missing or
            invalid values.
          </p>
          <p>This is an essential step in data preparation!</p>
          <p>Click on "NaN Remover" to add it.</p>
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
          <h3>Select Columns to Clean</h3>
          <p>Select all the columns to remove all the missing values (NaN).</p>
          <p>
            <strong>Click "Save" to apply the NaN Remover.</strong>
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
          <h3>Save Processed Dataset</h3>
          <p>
            After applying transformations, you can save your processed data as
            a new dataset.
          </p>
          <p>
            This creates a permanent copy with all your transformations applied,
            which you can use in the Models module.
          </p>
          <p>
            <strong>Click "Save as new Dataset" to continue.</strong>
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
          <h3>🎉 Final Step: Save Your Work</h3>
          <p>
            This modal shows all the transformations you've applied to your
            dataset.
          </p>
          <p>
            Give your new dataset a meaningful name and click "Save Dataset" to
            finish.
          </p>
          <hr style={{ margin: "15px 0", borderTop: "1px solid #ddd" }} />
          <h4>Congratulations! Tour Complete!</h4>
          <p>You've learned how to:</p>
          <ul style={{ marginBottom: "15px" }}>
            <li>✓ Explore and visualize your data</li>
            <li>✓ Transform and clean datasets</li>
            <li>✓ Save processed datasets for model training</li>
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
            <p style={{ margin: "0", fontWeight: "bold" }}>
              Next: Head to the Models module to train models with your prepared
              data! 🚀
            </p>
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
  locale: {
    back: "Back",
    close: "Close",
    last: "Finish",
    next: "Next",
    skip: "Skip Tour",
  },
};
