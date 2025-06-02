const nodeHelp = {
  Pipeline: {
    description: "Design a machine learning workflow by dragging and connecting nodes. Double-click a node to configure parameters."
  },
  DataSelector: {
    description: "Loads a dataset stored in the system to be used in the pipeline.",
    output: "Path to the selected dataset",
    next: "DataExploration, Train"
  },
  DataExploration: {
    description: "Analyzes the dataset to provide insights and visualizations.",
    input: "Selected dataset",
  },
  Train: {
    description: "Split dataset and train a model with specified parameters.",
    input: "Selected dataset",
    output: "Path to the trained model",
    next: "Prediction"
  },
  Prediction: {
    description: "Generates predictions using a trained model.",
    input: "Trained model",
  }
};

export function getNodeHelp(nodeType) {
  return nodeHelp[nodeType] || {
    description: "No description available.",
  };
}
