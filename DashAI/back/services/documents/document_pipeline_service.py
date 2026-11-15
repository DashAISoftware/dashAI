"""Validate and apply a batch-level converter pipeline to a document.

A pipeline is the same for every document of a batch. Each step names a
registered converter and its parameters; the content types it runs on are
derived from what the converter declares, so a caller never has to build the
scope by hand.
"""

import logging
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, TypedDict

from pydantic import ValidationError

from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.document_converter import DocumentConverter
from DashAI.back.converters.drop_source_columns import split_converter_params
from DashAI.back.core.data_kinds import DOCUMENT, supports_data_kind
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.dataloaders.classes.dashai_document import DashAIDocument
from DashAI.back.dataloaders.classes.document_items import (
    ItemFilter,
    ItemSelection,
    apply_converter_to_document,
)

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry import ComponentRegistry

log = logging.getLogger(__name__)

#: Metadata key under which the per-step report of a document is stored.
PIPELINE_METADATA_KEY = "converter_pipeline"
#: A step that ran on at least one content type.
APPLIED = "applied"
#: A step whose declared content types the document does not have.
SKIPPED = "skipped"


class PipelineStep(TypedDict):
    """One normalized step of a converter pipeline.

    Attributes
    ----------
    converter : str
        Registry name of the converter class.
    params : Dict[str, Any]
        Parameters the converter is instantiated with.
    """

    converter: str
    params: Dict[str, Any]


class PipelineReportEntry(TypedDict, total=False):
    """What a step did to one document.

    Attributes
    ----------
    converter : str
        Registry name of the converter class.
    status : str
        ``"applied"`` or ``"skipped"``.
    content_types : List[str]
        Content types the step ran on, or the ones it expected when skipped.
    reason : str
        Why the step was skipped; absent when it ran.
    """

    converter: str
    status: str
    content_types: List[str]
    reason: str


class DocumentPipelineInvalidError(ValueError):
    """A pipeline step cannot run on documents as configured (HTTP 422)."""


class DocumentPipelineDownloadError(RuntimeError):
    """A pipeline step uses a converter that was not downloaded (HTTP 409)."""


class DocumentPipelineService:
    """Validate a converter pipeline and apply it to a document.

    Parameters
    ----------
    component_registry : ComponentRegistry
        Registry used to resolve the converter classes and their download
        status.
    """

    def __init__(self, component_registry: "ComponentRegistry"):
        self._component_registry = component_registry

    def validate(self, pipeline: Optional[List[Any]]) -> Optional[List[PipelineStep]]:
        """Check every step and return the normalized pipeline.

        Validation covers the converter name, its data kind, supervised and
        row-changing restrictions, its parameters and its download status. It
        runs before a document is written, so an invalid pipeline leaves no
        rows behind.

        Parameters
        ----------
        pipeline : Optional[List[Any]]
            Steps as the request sent them, each with ``converter`` and
            ``params``. ``None`` and an empty list mean no pipeline.

        Returns
        -------
        Optional[List[PipelineStep]]
            A new list of steps with the converter name and the params the job
            must instantiate it with: defaults filled in, ``drop_source_columns``
            removed, and unknown keys refused. ``None`` when no pipeline was
            given.

        Raises
        ------
        DocumentPipelineInvalidError
            If a component is not a converter, runs on datasets only, is
            supervised, changes the row count without being a
            ``DocumentConverter``, or its parameters are unknown, invalid or
            refused by the constructor.
        DocumentPipelineDownloadError
            If a converter still has to be downloaded.
        """
        if not pipeline:
            return None
        normalized: List[PipelineStep] = []
        for step in pipeline:
            converter, params = self._read_step(step)
            converter_class = self._converter_class(converter)
            self._check_document_compatible(converter_class, converter)
            normalized_params = self._check_params(converter_class, params, converter)
            self._check_downloaded(converter_class, converter)
            normalized.append({"converter": converter, "params": normalized_params})
        return normalized

    def apply(
        self, document: DashAIDocument, pipeline: Optional[List[Any]]
    ) -> DashAIDocument:
        """Apply a validated pipeline to a document, step by step.

        Each step runs on every content type the converter declares that the
        document has. A step whose types are all absent is skipped and
        recorded, never treated as a failure. The report of the whole pipeline
        is stored under ``PIPELINE_METADATA_KEY`` in the returned document's
        metadata.

        Parameters
        ----------
        document : DashAIDocument
            The parsed document to convert.
        pipeline : Optional[List[Any]]
            The pipeline, in the order the steps must run.

        Returns
        -------
        DashAIDocument
            The converted document; the input is left unchanged.

        Raises
        ------
        DocumentPipelineInvalidError
            If the pipeline itself is invalid.
        DocumentPipelineDownloadError
            If a converter still has to be downloaded.
        """
        normalized = self.validate(pipeline)
        if normalized is None:
            return document
        report: List[PipelineReportEntry] = []
        converted = document
        for step in normalized:
            converter_class = self._converter_class(step["converter"])
            expected = self._declared_types(converter_class)
            present = self._present_types(converted)
            selected = self._selected_types(expected, present)
            if not selected:
                report.append(self._skip_entry(step["converter"], expected))
                continue
            selection: ItemSelection = {name: ItemFilter() for name in selected}
            converted = apply_converter_to_document(
                converted,
                self._make_converter(converter_class, step["params"]),
                selection,
            )
            report.append(
                {
                    "converter": step["converter"],
                    "status": APPLIED,
                    "content_types": selected,
                }
            )
        metadata = {**converted.metadata, PIPELINE_METADATA_KEY: report}
        return DashAIDocument(converted.tables, metadata)

    @staticmethod
    def _read_step(step: Any) -> Tuple[str, Dict[str, Any]]:
        """Read the converter name and params of one step.

        Parameters
        ----------
        step : Any
            A ``DocumentPipelineStep`` or its plain dict form.

        Returns
        -------
        tuple of (str, Dict[str, Any])
            The converter name and a copy of its params.

        Raises
        ------
        DocumentPipelineInvalidError
            If the step is malformed.
        """
        if hasattr(step, "model_dump"):
            data = step.model_dump()
        elif isinstance(step, Mapping):
            data = dict(step)
        else:
            raise DocumentPipelineInvalidError("Every pipeline step must be an object.")
        converter = data.get("converter")
        if not isinstance(converter, str) or not converter:
            raise DocumentPipelineInvalidError(
                "Every pipeline step needs a converter name."
            )
        raw_params = data.get("params") or {}
        if not isinstance(raw_params, dict):
            raise DocumentPipelineInvalidError(
                f"The parameters of {converter} must be an object."
            )
        params, _ = split_converter_params(raw_params)
        return converter, params

    @staticmethod
    def _make_converter(
        converter_class: type, params: Dict[str, Any]
    ) -> Callable[[], Any]:
        """Build the factory the conversion helper calls per content type.

        Parameters
        ----------
        converter_class : type
            The resolved converter class.
        params : Dict[str, Any]
            Validated parameters for this step.

        Returns
        -------
        Callable[[], Any]
            A factory returning a new configured converter.
        """

        def make() -> Any:
            return converter_class(**params)

        return make

    def _converter_class(self, name: str) -> type:
        """Resolve a converter class from the registry.

        Parameters
        ----------
        name : str
            Registry name of the converter.

        Returns
        -------
        type
            The converter class.

        Raises
        ------
        DocumentPipelineInvalidError
            If no such component is registered.
        """
        if name not in self._component_registry:
            raise DocumentPipelineInvalidError(f"Converter '{name}' does not exist.")
        return self._component_registry[name]["class"]

    @staticmethod
    def _check_document_compatible(converter_class: type, name: str) -> None:
        """Reject converters a document pipeline cannot run.

        Parameters
        ----------
        converter_class : type
            The resolved converter class.
        name : str
            Registry name, used in the error messages.

        Raises
        ------
        DocumentPipelineInvalidError
            If the component is not a converter, runs on datasets only, is
            supervised, or changes the row count without being a
            ``DocumentConverter``.
        """
        if not issubclass(converter_class, BaseConverter):
            raise DocumentPipelineInvalidError(f"'{name}' is not a converter.")
        if not supports_data_kind(converter_class, DOCUMENT):
            raise DocumentPipelineInvalidError(
                f"Converter {name} runs on datasets, not documents."
            )
        if getattr(converter_class, "SUPERVISED", False):
            raise DocumentPipelineInvalidError(
                f"Converter {name} is supervised and needs a target column, "
                "so it cannot run on a document."
            )
        if getattr(converter_class, "CHANGES_ROW_COUNT", False) and not issubclass(
            converter_class, DocumentConverter
        ):
            raise DocumentPipelineInvalidError(
                f"Converter {name} changes the number of rows, which only a "
                "DocumentConverter can do on a document."
            )

    @staticmethod
    def _check_params(
        converter_class: type, params: Dict[str, Any], name: str
    ) -> Dict[str, Any]:
        """Validate the parameters and return the values to store.

        Unknown top-level keys are refused instead of silently dropped, the
        schema fills the missing values, and the converter is constructed once
        so a constructor-level error is reported here rather than by the job.

        Parameters
        ----------
        converter_class : type
            The resolved converter class.
        params : Dict[str, Any]
            Parameters of the step.
        name : str
            Registry name, used in the error messages.

        Returns
        -------
        Dict[str, Any]
            The validated parameters, with schema defaults filled in and
            ``drop_source_columns`` removed.

        Raises
        ------
        DocumentPipelineInvalidError
            If a key is unknown, a value does not validate, or the constructor
            refuses the values.
        """
        properties = converter_class.get_schema().get("properties", {})
        unknown = []
        for key in params:
            if key not in properties:
                unknown.append(key)
        if unknown:
            raise DocumentPipelineInvalidError(
                f"Unknown parameters for {name}: {', '.join(sorted(unknown))}."
            )
        merged = {**schema_placeholder_defaults(converter_class), **params}
        try:
            validated = converter_class.SCHEMA.model_validate(merged)
        except ValidationError as e:
            raise DocumentPipelineInvalidError(
                f"Invalid parameters for {name}: {e}"
            ) from e
        normalized, _ = split_converter_params(validated.model_dump())
        try:
            converter_class(**normalized)
        except Exception as e:
            raise DocumentPipelineInvalidError(
                f"Invalid parameters for {name}: {e}"
            ) from e
        return normalized

    def _check_downloaded(self, converter_class: type, name: str) -> None:
        """Reject a converter whose artifacts are not downloaded.

        Parameters
        ----------
        converter_class : type
            The resolved converter class.
        name : str
            Registry name, used in the error message.

        Raises
        ------
        DocumentPipelineDownloadError
            If the converter needs a download that is not present.
        """
        requires = getattr(converter_class, "REQUIRES_DOWNLOAD", False)
        if requires and not self._component_registry.refresh_download_status(name):
            raise DocumentPipelineDownloadError(
                f"Converter {name} must be downloaded before use."
            )

    @staticmethod
    def _declared_types(converter_class: type) -> Optional[List[str]]:
        """Return the content types a converter declares, by display name.

        ``document_allowed_types`` wins over ``allowed_types``; both empty
        means the converter takes every content type the document has.

        Parameters
        ----------
        converter_class : type
            The resolved converter class.

        Returns
        -------
        Optional[List[str]]
            Declared content type names, or ``None`` when unrestricted.
        """
        metadata = converter_class.get_metadata()
        declared = (
            metadata.get("document_allowed_types")
            or metadata.get("allowed_types")
            or []
        )
        return list(declared) or None

    @staticmethod
    def _present_types(document: DashAIDocument) -> List[str]:
        """Return the content type names the document has items of.

        Parameters
        ----------
        document : DashAIDocument
            The document being converted.

        Returns
        -------
        List[str]
            Display names of the content types with at least one item.
        """
        present: List[str] = []
        for content_type in DashAIDocument.SUPPORTED_TYPES:
            if document.count(content_type) > 0:
                present.append(content_type.display_name())
        return present

    @staticmethod
    def _selected_types(expected: Optional[List[str]], present: List[str]) -> List[str]:
        """Pick the content types a step runs on.

        Parameters
        ----------
        expected : Optional[List[str]]
            Types the converter declares, or ``None`` for every present type.
        present : List[str]
            Types the document has items of.

        Returns
        -------
        List[str]
            The declared types the document has, or every present type when
            the converter declares none.
        """
        if expected is None:
            return list(present)
        selected: List[str] = []
        for name in expected:
            if name in present:
                selected.append(name)
        return selected

    @staticmethod
    def _skip_entry(
        converter: str, expected: Optional[List[str]]
    ) -> PipelineReportEntry:
        """Build the report entry of a step with no items to convert.

        Parameters
        ----------
        converter : str
            Registry name of the converter.
        expected : Optional[List[str]]
            Types the converter declares, or ``None``.

        Returns
        -------
        PipelineReportEntry
            The skipped step and why.
        """
        content_types = list(expected or [])
        if content_types:
            reason = f"The document has no {', '.join(content_types)} items."
        else:
            reason = "The document has no items to convert."
        return {
            "converter": converter,
            "status": SKIPPED,
            "content_types": content_types,
            "reason": reason,
        }
