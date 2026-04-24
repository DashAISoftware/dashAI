# flake8: noqa
# Not implemented yet
from dataclasses import dataclass
from typing import Optional

from DashAI.back.types.dashai_data_type import DashAIDataType


@dataclass
class DashAIImage(DashAIDataType):
    """
    Represents an image data type in DashAI.

    Attributes
    ----------
    dtype : str
        The data type of the image, default is "struct" (Arrow struct<bytes: binary, format: string>).
    base_path : Optional[str]
        An optional base path for images.
    """

    dtype: str = "struct"
    base_path: Optional[str] = None

    def __init__(self, dtype: str = "struct"):
        self.dtype = dtype

    def to_string(self):
        """
        Convert the DashAIImage type to a string representation.

        Returns
        -------
        dict
            A dictionary representation of the DashAIImage type.
        """
        if self.base_path:
            return {"type": "Image", "dtype": self.dtype, "base_path": self.base_path}

        return {"type": "Image", "dtype": self.dtype}
