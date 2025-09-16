export const generateDatasetName = (existingDatasets = []) => {
  const baseName = "Dataset";

  const namePattern = new RegExp(`^${baseName}_(\\d+)$`);
  const existingNumbers = existingDatasets
    .map((dataset) => {
      const match = dataset.name?.match(namePattern);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((num) => num !== null);

  const maxNumber =
    existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const nextNumber = maxNumber + 1;

  const generatedName = `${baseName}_${nextNumber}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
};

export const generateExperimentName = (existingExperiments = []) => {
  const baseName = "Experiment";

  const namePattern = new RegExp(`^${baseName}_(\\d+)$`);
  const existingNumbers = existingExperiments
    .map((experiment) => {
      const match = experiment.name.match(namePattern);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((num) => num !== null);

  const maxNumber =
    existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const nextNumber = maxNumber + 1;

  const generatedName = `${baseName}_${nextNumber}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
};

export const generateModelName = (selectedModel, existingRuns = []) => {
  if (!selectedModel) {
    return { defaultName: "Model_1", placeholderName: "Model_1" };
  }

  const baseName = selectedModel;

  const runsForModel = existingRuns.filter(
    (run) => run.model === selectedModel,
  );

  const namePattern = new RegExp(`^${baseName}_(\\d+)$`);
  const existingNumbers = runsForModel
    .map((run) => {
      const match = run.name.match(namePattern);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((num) => num !== null);

  const maxNumber =
    existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const nextNumber = maxNumber + 1;

  const generatedName = `${baseName}_${nextNumber}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
};

export const generateNotebookName = (
  selectedDataset,
  existingNotebooks = [],
) => {
  if (!selectedDataset) {
    return { defaultName: "Notebook_1", placeholderName: "Notebook_1" };
  }

  const baseName = `Notebook_${selectedDataset.name}`;

  const notebooksForDataset = existingNotebooks.filter(
    (notebook) => notebook.dataset_id === selectedDataset.id,
  );

  const namePattern = new RegExp(`^${baseName}_(\\d+)$`);
  const existingNumbers = notebooksForDataset
    .map((notebook) => {
      const match = notebook.name.match(namePattern);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((num) => num !== null);

  const maxNumber =
    existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const nextNumber = maxNumber + 1;

  const generatedName = `${baseName}_${nextNumber}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
};

export const generatePredictionName = (existingPredictions = []) => {
  const baseName = "Prediction";

  const namePattern = new RegExp(`^${baseName}_(\\d+)(?:\\.json)?$`);

  const existingNumbers = existingPredictions
    .map((prediction, index) => {
      const predName = prediction.pred_name;

      if (!predName) return null;

      const match = predName.match(namePattern);
      const number = match ? parseInt(match[1], 10) : null;

      return number;
    })
    .filter((num) => num !== null);

  const maxNumber =
    existingNumbers.length > 0 ? Math.max(...existingNumbers) : 0;
  const nextNumber = maxNumber + 1;

  const generatedName = `${baseName}_${nextNumber}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
};

export function generateSequentialName({
  base,
  items = [],
  getName = (item) => item.name,
  filter = () => true,
  allowExtension = false, // útil para .json
  startAt = 1,
}) {
  const escapedBase = base.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const extPart = allowExtension ? "(?:\\.[^.]+)?" : "";
  const regex = new RegExp(`^${escapedBase}_(\\d+)${extPart}$`, "i");

  const numbers = items
    .filter(filter)
    .map((item) => {
      const name = getName(item) || "";
      const match = name.match(regex);
      return match ? parseInt(match[1], 10) : null;
    })
    .filter((n) => n !== null);

  const max = numbers.length ? Math.max(...numbers) : startAt - 1;
  const next = max + 1;

  const generatedName = `${base}_${next}`;

  return {
    defaultName: generatedName,
    placeholderName: generatedName,
  };
}
