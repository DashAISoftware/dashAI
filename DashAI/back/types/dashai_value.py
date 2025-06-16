from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from DashAI.back.types.dashai_data_type import DashAIDataType
from datasets import Value

@dataclass
class DashAIValue(DashAIDataType):
    pass