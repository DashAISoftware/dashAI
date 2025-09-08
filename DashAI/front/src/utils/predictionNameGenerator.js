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
