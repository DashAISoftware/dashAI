from typing import Dict, List, Union

import numpy as np
import pandas as pd

from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.types.inf.inference_methods import (
    DashAIPtype,
    DummyCategoricalInference,
)

AcceptedDataInput = Union[
    pd.DataFrame,
    np.ndarray,
    List[dict],
    List[List],
    Dict[str, List],
    DashAIDataset,
]

AcceptedMethods = {
    "DashAIPtype": DashAIPtype,
    "Dummy": DummyCategoricalInference,
}


def infer_types(data: AcceptedDataInput, method: str) -> dict:
    """
    Infers types from the provided data using the specified inference method.

    Parameters
    ----------
    data : AcceptedDataInput
        The input data for type inference, which can be a pandas DataFrame,
        numpy array, list of dictionaries, list of lists, or dictionary of lists.
    method : AcceptedMethods
        The inference method to use for type inference, which can be an instance
        of DashAIPtype or other defined methods.
    Returns
    -------
    dict
        A dictionary mapping column names to inferred types.
    """
    if method not in AcceptedMethods:
        raise ValueError(
            f"Method '{method}' is not supported. "
            f"Available methods: {list(AcceptedMethods.keys())}"
        )

    infer_method = AcceptedMethods[method]()

    return infer_method.infer_types(data)
