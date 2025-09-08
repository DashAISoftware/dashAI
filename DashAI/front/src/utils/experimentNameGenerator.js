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
