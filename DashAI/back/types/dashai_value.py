from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from DashAI.back.types.dashai_data_type import DashAIDataType
from datasets import Value


# @dataclass
# class DashAIValue(ABC, Value):
#     dtype: str = field(default="", init=False)

#     @abstractmethod
#     def __post_init__(self):
#         return super().__post_init__()

#     @staticmethod
#     @abstractmethod
#     def from_value(value: Value) -> "DashAIValue":
#         raise NotImplementedError

@dataclass
class DashAIValue(DashAIDataType):
    pass