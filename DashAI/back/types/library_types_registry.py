import value_types as vt
import pyarrow as pa
from DashAI.back.types.value_types import DashAIDataType, Integer, Float, Text, Time, Boolean, Timestamp, Duration, Decimal, Date, Binary
from collections import defaultdict
import pandas as pd
import numpy as np
import torch

registry = {}

def register_transform(data_type: DashAIDataType, backend):
    """Register a transformation for a DashAIDataType to a specific backend."""
    def decorator(func):
        if DashAIDataType not in registry:
            registry[DashAIDataType] = {}
        registry[data_type][backend] = func
        return func
    return decorator

def get_transform(data_type: DashAIDataType, backend: str):
    """Get the transformation function for a DashAIDataType to a specific backend."""
    if data_type in registry and backend in registry[data_type]:
        return registry[data_type][backend]
    raise ValueError(f"No transformation registered for {data_type} to {backend}")


#sklearn transformations
@register_transform(Integer, "sklearn")
def transform_integer_to_sklearn(value: Integer):
    """Transform Integer to a format compatible with sklearn."""
    return int(value.value)
