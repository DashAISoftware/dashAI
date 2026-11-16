"""Shared pieces of tools that run one downloadable pretrained model."""

from typing import Any, Iterator, List, Optional, Sequence

from DashAI.back.core.schema_fields import enum_field, schema_field
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dependencies.downloads.downloadable import HFPretrainedDownloadMixin
from DashAI.back.models.utils import DEVICE_ENUM, DEVICE_PLACEHOLDER, DEVICE_TO_IDX


def device_field() -> Any:
    """Return the schema field that picks the device a model runs on.

    Returns
    -------
    Any
        A ``device`` field over the available GPUs and the CPU.
    """
    return schema_field(
        enum_field(DEVICE_ENUM),
        DEVICE_PLACEHOLDER,
        description=MultilingualString(
            en=(
                "Device the model runs on. GPU choices appear when PyTorch is "
                "installed with CUDA support."
            ),
            es=(
                "Dispositivo en el que corre el modelo. Las GPU aparecen si "
                "PyTorch está instalado con soporte CUDA."
            ),
            pt=(
                "Dispositivo em que o modelo roda. As GPUs aparecem quando o "
                "PyTorch está instalado com suporte a CUDA."
            ),
            de=(
                "Gerät, auf dem das Modell läuft. GPUs werden angezeigt, wenn "
                "PyTorch mit CUDA-Unterstützung installiert ist."
            ),
            zh="模型运行的设备。只有安装了支持 CUDA 的 PyTorch 才会显示 GPU。",
        ),
        alias=MultilingualString(
            en="Device",
            es="Dispositivo",
            pt="Dispositivo",
            de="Gerät",
            zh="设备",
        ),
    )


TORCH_DEVICE_CPU = "cpu"
TORCH_DEVICE_CUDA_PREFIX = "cuda"


def torch_device(label: Optional[str]) -> str:
    """Turn a device label of :func:`device_field` into a torch device.

    Parameters
    ----------
    label : str, optional
        A label such as ``"CPU"`` or ``"GPU 0: ..."``; None means CPU.

    Returns
    -------
    str
        ``"cuda:<index>"`` or ``"cpu"``.
    """
    index = DEVICE_TO_IDX.get(label or "CPU", -1)
    if index >= 0:
        return f"{TORCH_DEVICE_CUDA_PREFIX}:{index}"
    return TORCH_DEVICE_CPU


def batches(values: Sequence[Any], size: int) -> Iterator[List[Any]]:
    """Yield consecutive slices of at most ``size`` values.

    Parameters
    ----------
    values : Sequence[Any]
        The values to slice.
    size : int
        The largest slice.

    Yields
    ------
    List[Any]
        The next slice.
    """
    for start in range(0, len(values), size):
        yield list(values[start : start + size])


def open_image(value: Any) -> Any:
    """Decode a stored image value into an RGB PIL image.

    Parameters
    ----------
    value : dict or DashAIImage
        A ``{"bytes", "path"}`` value or an object with ``bytes``.

    Returns
    -------
    PIL.Image.Image
        The image in RGB mode.
    """
    import io

    from PIL import Image

    data = value["bytes"] if isinstance(value, dict) else value.bytes
    return Image.open(io.BytesIO(data)).convert("RGB")


class PretrainedTool(HFPretrainedDownloadMixin):
    """A component that runs one Hugging Face model, loaded on first use.

    Subclasses set ``MODEL_NAME`` and ``DOWNLOAD_SIZE_BYTES`` and implement
    :meth:`load_pretrained`. The model is read from the component's download
    folder when it was downloaded, or from the Hub otherwise.
    """

    def setup_device(self, label: Optional[str]) -> None:
        """Choose the device and forget any loaded model.

        Parameters
        ----------
        label : str, optional
            The ``device`` parameter.
        """
        self.device = torch_device(label)
        self._pretrained: Any = None

    def load_pretrained(self, source: str) -> Any:
        """Load the model and its processor.

        Parameters
        ----------
        source : str
            A local directory or a Hub repo id.

        Returns
        -------
        Any
            Whatever the tool needs to run, such as a ``(processor, model)``
            pair.
        """
        raise NotImplementedError

    def pretrained(self) -> Any:
        """Return the loaded model, loading it on first use.

        Returns
        -------
        Any
            The value :meth:`load_pretrained` returned.
        """
        if getattr(self, "_pretrained", None) is None:
            self._pretrained = self.load_pretrained(self._pretrained_source())
        return self._pretrained
