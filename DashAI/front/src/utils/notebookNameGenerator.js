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
