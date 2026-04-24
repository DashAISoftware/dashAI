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
        The data type of the image, default is "string" which represents the path to the image.
    base_path : Optional[str]
        An optional base path for images, useful if images are represented just by their filenames.
    """

    dtype: str = "string"  # Default: Path to image (str)
    ####
    # Optional base path in case images are represented just by their filenames
    # Since Dataloaders are not something I'm working on,
    # this was done in the basis that the final image dataloader
    # will contain an optional parameter to specify a base path for images
    # (If they are in the same folder, for example).
    base_path: Optional[str] = None
    ####

    def __init__(self, dtype: str = "string"):
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
