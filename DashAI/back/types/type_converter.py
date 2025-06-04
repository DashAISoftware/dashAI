from typing import Tuple
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


def transform_targets(
    dataset: DashAIDataset,
    model_type: str
) -> DashAIDataset:
    """Transform the target dataset to a format suitable for the model.

    Parameters
    ----------
    dataset : DashAIDataset
        The target dataset to be transformed.
    model_type : str
        The type of model used for classification, e.g., "sklearn", "tensorflow", etc.

    Returns
    -------
    DashAIDataset
        The transformed target dataset.
    """
    if model_type == "sklearn":
        return dataset.to_pandas()  # Assuming sklearn-like models use pandas DataFrame
    else:
        raise NotImplementedError(f"Model type '{model_type}' is not supported.")