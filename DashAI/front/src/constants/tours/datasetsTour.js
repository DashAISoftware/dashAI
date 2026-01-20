import React from "react";

export const datasetsTourSteps = [
  {
    target: "body",
    content: (
      <div>
        <h3>Dataset Module</h3>
        <p>
          This is where you manage your data and create interactive notebooks
          for analysis. Let's see how to get started!
        </p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
  },
  {
    target: '[data-tour="dataset-option"]',
    content: (
      <div>
        <h3>Upload Dataset</h3>
        <p>
          This is where you import your own files from various formats and
          sources.
        </p>
        <p>You can upload CSV, Excel, and other common data formats.</p>
      </div>
    ),
    placement: "bottom",
  },
  {
    target: '[data-tour="notebook-option"]',
    content: (
      <div>
        <h3>Create Notebook</h3>
        <p>This lets you explore or transform datasets interactively.</p>
        <p>
          Notebooks are where you visualize data, apply transformations, and
          prepare it for modeling.
        </p>
      </div>
    ),
    placement: "bottom",
  },
  {
    target: "body",
    content: (
      <div>
        <h3>Download Sample Dataset</h3>
        <p>To get started quickly, let's download a sample dataset.</p>
        <p>
          <a
            href="/samples/personality_dataset.csv"
            download="personality_dataset.csv"
            style={{
              display: "inline-block",
              backgroundColor: "#1976d2",
              color: "white",
              padding: "10px 20px",
              textDecoration: "none",
              borderRadius: "4px",
              fontWeight: "bold",
              marginTop: "10px",
            }}
            onMouseOver={(e) => (e.target.style.backgroundColor = "#1565c0")}
            onMouseOut={(e) => (e.target.style.backgroundColor = "#1976d2")}
          >
            Download Personality_Dataset.csv
          </a>
        </p>
        <p style={{ fontSize: "0.9em", color: "#666" }}>
          💡 <strong>Tip:</strong> The file will be saved to your Downloads
          folder by default.
        </p>
        <p style={{ marginTop: "10px" }}>
          Once downloaded, click "Next" to learn how to upload it!
        </p>
      </div>
    ),
    placement: "center",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: false,
  },
  {
    target: '[data-tour="dataset-option"]',
    content: (
      <div>
        <h3>Now Let's Upload It</h3>
        <p>
          Now that you've downloaded the sample dataset, let's upload it to
          DashAI.
        </p>
        <p>
          <strong>Click "Upload Dataset" to begin the upload process.</strong>
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
    disableOverlayClose: true,
    isInteractive: true,
  },
  {
    target: '[data-tour="csv-dataloader-option"]',
    content: (
      <div>
        <h3>Select CSV DataLoader</h3>
        <p>
          Since our sample dataset is a CSV file, we need to select the{" "}
          <strong>CSVDataLoader</strong>.
        </p>
        <p>
          DataLoaders are tools that help DashAI understand and process
          different file formats.
        </p>
        <p>
          <strong>Click on "CSVDataLoader" to select it.</strong>
        </p>
      </div>
    ),
    placement: "right",
    disableBeacon: true,
    spotlightClicks: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="dataloader-step-next-button"]',
    content: (
      <div>
        <h3>Continue to Upload</h3>
        <p>
          With the CSVDataLoader selected, click "Next" to proceed to the upload
          configuration.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
    isInteractive: true,
  },

  {
    target: '[data-tour="upload-area"]',
    content: (
      <div>
        <h3>Upload Your File</h3>
        <p>Now it's time to upload the file you just downloaded!</p>
        <ul>
          <li>
            Click <strong>"Upload a file"</strong> to browse for it
          </li>
        </ul>
        <p style={{ fontSize: "0.9em", color: "#666", marginTop: "10px" }}>
          💡 Look for "personality_dataset.csv" in your Downloads folder.
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
    disableBackButton: true,
  },
  {
    target: '[data-tour="dataloader-config"]',
    content: (
      <div>
        <h3>DataLoader Configuration</h3>
        <p>Here you can configure how the dataset should be loaded:</p>
        <ul>
          <li>
            <strong>Name:</strong> Give your dataset a meaningful name
          </li>
          <li>
            <strong>Separator:</strong> The character that separates values
            (comma for CSV)
          </li>
          <li>
            <strong>Other options:</strong> Advanced settings for specific needs
          </li>
        </ul>
        <p
          style={{
            backgroundColor: "#e8f5e9",
            padding: "8px",
            borderRadius: "4px",
            marginTop: "10px",
          }}
        >
          💡 <strong>Pro tip:</strong> The default settings work well for most
          CSV files, so you can usually leave them as they are!
        </p>
      </div>
    ),
    placement: "left",
    disableBeacon: true,
    spotlightClicks: true,
  },
  {
    target: '[data-tour="dataset-step-upload-button"]',
    content: (
      <div>
        <h3>Complete the Upload</h3>
        <p>
          Once you've uploaded the file and reviewed the configuration, click{" "}
          <strong>"Upload"</strong> to process your dataset.
        </p>
        <p>
          DashAI will analyze the file structure and prepare it for exploration
          and analysis.
        </p>
      </div>
    ),
    placement: "top",
    disableBeacon: true,
    spotlightClicks: true,
    hideFooter: true,
  },

  {
    target: ".datasets-list",
    content: (
      <div>
        <h3>Your Datasets</h3>
        <p>The Personality dataset is now available in your Datasets list.</p>
        <p>
          You can find all your uploaded datasets and notebooks in this sidebar.
        </p>
      </div>
    ),
    placement: "right",
    disableBackButton: true,
  },
  {
    target: '[data-tour="datasets-new-notebook-button"]',
    content: (
      <div>
        <h3>Next Steps: Create a Notebook</h3>
        <p>
          Now click "New Notebook" to open the dataset in an interactive
          environment.
        </p>
        <p>
          In a notebook, you can analyze, visualize, and transform your data.
        </p>
      </div>
    ),
    placement: "bottom",
    spotlightClicks: true,
    disableOverlayClose: true,
    hideFooter: true,
  },
  {
    target: ".notebook-note-box",
    content: (
      <div>
        <h3>Important Note</h3>
        <p>Pay attention to this information</p>
        <p>
          This ensures your original data remains intact while you experiment.
        </p>
      </div>
    ),
    placement: "bottom",
    disableBeacon: true,
    disableOverlayClose: true,
    disableCloseOnEsc: true,
  },
  {
    target: '[data-tour="create-notebook-button"]',
    content: (
      <div>
        <h3>Finish the Process</h3>
        <p>
          Click "Create Notebook" to start working with your data in an
          interactive environment.
        </p>
        <p>
          You'll be able to visualize, transform, and prepare your data for
          modeling.
        </p>
      </div>
    ),
    placement: "top",
    spotlightClicks: true,
    disableOverlayClose: true,
    disableBeacon: true,
  },
];

export const datasetsTourConfig = {
  continuous: true,
  showProgress: true,
  showSkipButton: true,
  showBackButton: true,
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
