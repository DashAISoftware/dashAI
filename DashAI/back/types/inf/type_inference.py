from abc import ABC, abstractmethod
from typing import Dict, Any, Union, List
import pandas as pd
import numpy as np
from DashAI.back.types.inf.inference_methods import DashAIPtype

        

AcceptedDataInput = Union[
    pd.DataFrame,
    np.ndarray,
    List[dict],
    List[List],
    Dict[str, List],
]

AcceptedMethods = Union[
    DashAIPtype,
    # Add other inference methods here as needed
]


def infer_types(
    data: AcceptedDataInput, 
    method: AcceptedMethods
) -> dict:
    """
    """
    infer_method = method()

    if isinstance(infer_method, DashAIPtype):
        return infer_method.infer_types(data)

