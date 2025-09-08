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
