"""Base classes for DashAI dataset exporters."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields import schema_field, string_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
    from DashAI.back.types.dashai_data_type import DashAIDataType


class CompatibilityStatus(str, Enum):
    """How well a dataset fits an export platform."""

    COMPATIBLE = "compatible"
    WARNING = "warning"
    INCOMPATIBLE = "incompatible"


@dataclass
class DatasetCompatibility:
    """Whether a dataset can be exported to a platform, judged by its columns.

    Parameters
    ----------
    status : CompatibilityStatus
        ``compatible``: exported as is. ``warning``: exported, but something
        is left out. ``incompatible``: cannot be exported.
    messages : list[str]
        Human readable reasons for a warning or incompatibility.
    unsupported_columns : list[str]
        Columns the platform cannot store and would be left out.
    """

    status: CompatibilityStatus = CompatibilityStatus.COMPATIBLE
    messages: list[str] = field(default_factory=list)
    unsupported_columns: list[str] = field(default_factory=list)


@dataclass
class ExportPayload:
    """Platform ready content produced by an exporter before uploading.

    Parameters
    ----------
    files : list[str]
        Paths of the files generated for the upload.
    metadata : dict[str, Any]
        Metadata already formatted for the target platform.
    """

    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of publishing a dataset to an external platform.

    Parameters
    ----------
    remote_id : str
        Identifier assigned to the dataset by the platform.
    url : str
        Public link to the published dataset.
    detail : dict[str, Any]
        Extra platform specific information returned by the upload.
    """

    remote_id: str
    url: str
    detail: dict[str, Any] = field(default_factory=dict)


class DatasetExportValidationError(ValueError):
    """Raised when a dataset or its export parameters fail validation.

    Parameters
    ----------
    errors : list[str]
        Human readable validation errors.
    """

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class BaseDatasetExportSchema(BaseSchema):
    """Parameters shared by every dataset export platform."""

    name: schema_field(
        string_field(),
        "",
        description=MultilingualString(
            en="Name the dataset will have on the target platform.",
            es="Nombre que tendrá el dataset en la plataforma de destino.",
            pt="Nome que o conjunto de dados terá na plataforma de destino.",
            de="Name, den der Datensatz auf der Zielplattform haben wird.",
            zh="数据集在目标平台上的名称。",
        ),
        alias=MultilingualString(
            en="Name", es="Nombre", pt="Nome", de="Name", zh="名称"
        ),
    )  # type: ignore
    description: schema_field(
        string_field(),
        "",
        description=MultilingualString(
            en="Description of the dataset shown on the target platform.",
            es="Descripción del dataset que se mostrará en la plataforma de destino.",
            pt="Descrição do conjunto de dados exibida na plataforma de destino.",
            de="Beschreibung des Datensatzes auf der Zielplattform.",
            zh="在目标平台上显示的数据集描述。",
        ),
        alias=MultilingualString(
            en="Description",
            es="Descripción",
            pt="Descrição",
            de="Beschreibung",
            zh="描述",
        ),
    )  # type: ignore


class BaseDatasetExporter(ConfigObject, ABC):
    """Abstract base class for all DashAI dataset exporters.

    Subclasses publish a DashAI dataset to an external platform (OpenML,
    HuggingFace Hub, Zenodo, etc.). They only implement :meth:`prepare` and
    :meth:`upload`; :meth:`export` runs the full validate, prepare and upload
    sequence and is not meant to be overridden.
    """

    TYPE: Final[str] = "DatasetExporter"
    DISPLAY_NAME: Final = MultilingualString(en="", es="", zh="", pt="", de="")
    DESCRIPTION: Final = MultilingualString(en="", es="", zh="", pt="", de="")
    SCHEMA = BaseDatasetExportSchema
    REQUIRED_CREDENTIALS: list[str] = []
    SOURCE_NAME: str | None = None

    def check_dataset(
        self, column_types: dict[str, "DashAIDataType"]
    ) -> DatasetCompatibility:
        """Judge whether a dataset fits this platform from its column types.

        Unlike :meth:`validate`, it needs no export parameters and no data, so
        it can run over every dataset to tell the user up front which ones the
        platform accepts. The default implementation accepts every dataset.

        Parameters
        ----------
        column_types : dict[str, DashAIDataType]
            DashAI type of each column, in column order.

        Returns
        -------
        DatasetCompatibility
            Status, reasons and the columns that would be left out.
        """
        return DatasetCompatibility()

    def validate(self, dataset: "DashAIDataset", params: dict[str, Any]) -> list[str]:
        """Check the dataset and export parameters before exporting.

        The default implementation rejects empty datasets and blank names or
        descriptions. Subclasses extend it with platform specific rules and
        should include the errors returned by ``super().validate``.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to export.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.

        Returns
        -------
        list[str]
            Validation errors. An empty list means the export can proceed.
        """
        errors = []
        if dataset.num_rows == 0:
            errors.append("The dataset has no rows.")
        if not str(params.get("name", "")).strip():
            errors.append("The dataset name cannot be blank.")
        if not str(params.get("description", "")).strip():
            errors.append("The dataset description cannot be blank.")
        return errors

    @abstractmethod
    def prepare(
        self, dataset: "DashAIDataset", params: dict[str, Any], temp_path: str
    ) -> ExportPayload:
        """Convert the dataset into the format required by the platform.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to export.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.
        temp_path : str
            Local directory where generated files can be written.

        Returns
        -------
        ExportPayload
            Files and metadata ready to be uploaded.
        """
        ...

    @abstractmethod
    def upload(self, payload: ExportPayload, params: dict[str, Any]) -> ExportResult:
        """Publish the prepared payload to the platform.

        Parameters
        ----------
        payload : ExportPayload
            Content returned by :meth:`prepare`.
        params : dict[str, Any]
            Export parameters, already validated against :attr:`SCHEMA`.

        Returns
        -------
        ExportResult
            Identifier and public link of the published dataset.
        """
        ...

    def export(
        self,
        dataset: "DashAIDataset",
        params: dict[str, Any],
        temp_path: str,
        on_step: Callable[[str], None] | None = None,
    ) -> ExportResult:
        """Validate, prepare and upload a dataset.

        This is the entry point used by the export job. Subclasses customize
        :meth:`validate`, :meth:`prepare` and :meth:`upload` instead of
        overriding this method.

        Parameters
        ----------
        dataset : DashAIDataset
            Dataset to export.
        params : dict[str, Any]
            Raw export parameters as sent by the user.
        temp_path : str
            Local directory where generated files can be written.
        on_step : Callable[[str], None] or None, optional
            Called with ``"prepare"`` right before :meth:`prepare` and with
            ``"upload"`` right before :meth:`upload`, so the caller can track
            the export phase. By default nothing is called.

        Returns
        -------
        ExportResult
            Identifier and public link of the published dataset.

        Raises
        ------
        pydantic.ValidationError
            If ``params`` does not match :attr:`SCHEMA`.
        DatasetExportValidationError
            If :meth:`validate` reports errors.
        """
        params = self.SCHEMA.model_validate(params).model_dump()
        errors = self.validate(dataset, params)
        if errors:
            raise DatasetExportValidationError(errors)
        if on_step is not None:
            on_step("prepare")
        payload = self.prepare(dataset, params, temp_path)
        if on_step is not None:
            on_step("upload")
        return self.upload(payload, params)

    def get_remote_status(self, remote_id: str) -> str | None:
        """Return the status of a published dataset on the platform.

        The default implementation returns None, meaning the platform does
        not report a processing status.

        Parameters
        ----------
        remote_id : str
            Identifier returned in :attr:`ExportResult.remote_id`.

        Returns
        -------
        str or None
            Platform specific status, or None if unsupported.
        """
        return None
