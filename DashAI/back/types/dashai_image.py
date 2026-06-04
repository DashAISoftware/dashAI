"""DashAI Image type."""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Optional

import pyarrow as pa

from DashAI.back.types.dashai_data_type import DashAIDataType

if TYPE_CHECKING:
    import numpy as np
    from PIL import Image as PILImage


@dataclass
class DashAIImage(DashAIDataType):
    """Image type for DashAI datasets.

    Serves dual roles:
    - Column type descriptor: ``DashAIImage()`` — bytes/path are None.
    - Data instance returned by ``DashAIDataset.__getitem__``:
      ``DashAIImage(bytes=b"...", path="cat.jpg")``.
    """

    pa_type: ClassVar[pa.DataType] = pa.struct(
        {"bytes": pa.binary(), "path": pa.string()}
    )

    dtype: str = "struct"
    bytes: Optional[bytes] = field(default=None, repr=False)
    path: Optional[str] = field(default=None, repr=False)

    def to_string(self) -> dict:
        return {"type": "Image", "dtype": self.dtype}

    def to_pil(self) -> "PILImage":
        """Decode image bytes to a PIL Image."""
        from PIL import Image as PILImage

        if self.bytes is None:
            raise ValueError("No image bytes available.")
        return PILImage.open(io.BytesIO(self.bytes))

    def to_numpy(self) -> "np.ndarray":
        """Decode image bytes to a NumPy array (H x W x C, uint8)."""
        import numpy as np

        return np.array(self.to_pil())
