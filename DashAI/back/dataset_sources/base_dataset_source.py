"""Base classes for DashAI dataset sources."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.utils import MultilingualString


@dataclass
class DatasetEntry:
    """Represents a single dataset retrieved from an external source.

    Parameters
    ----------
    id : str
        Source-specific unique identifier (e.g. ``"owner/name"`` for HuggingFace).
    name : str
        Human-readable dataset name.
    description : str
        Short description of the dataset.
    tags : list[str]
        List of topic/task tags.
    size_bytes : int or None
        Total compressed size in bytes, or None if unknown.
    row_count : int or None
        Number of rows, or None if unknown.
    url : str
        Link to the dataset page on the source website.
    source : str
        Class name of the DatasetSource that produced this entry.
    """

    id: str
    name: str
    description: str
    tags: list[str]
    size_bytes: int | None
    row_count: int | None
    url: str
    source: str


class BaseDatasetSource(ConfigObject, ABC):
    """Abstract base class for all DashAI dataset sources.

    Subclasses connect to external dataset repositories (HuggingFace Hub,
    OpenML, Kaggle, etc.) and expose a uniform interface for searching,
    previewing, and downloading datasets.
    """

    TYPE: Final[str] = "DatasetSource"
    DISPLAY_NAME: Final = MultilingualString(en="", es="")
    DESCRIPTION: Final = MultilingualString(en="", es="")

    @abstractmethod
    def search(
        self, query: str, limit: int = 20, offset: int = 0, **filters: Any
    ) -> list[DatasetEntry]:
        """Return datasets matching a query string.

        Parameters
        ----------
        query : str
            Free-text search string.
        limit : int, optional
            Maximum number of results, by default 20.
        offset : int, optional
            Number of results to skip (for pagination), by default 0.
        **filters : Any
            Source-specific filter keyword arguments.

        Returns
        -------
        list[DatasetEntry]
            Matching datasets from this source.
        """
        ...

    def get_info(self, dataset_id: str) -> DatasetEntry | None:
        """Return full metadata for a single dataset, including description and tags.

        The default implementation returns None (no enrichment).
        Sources that require extra requests to retrieve description/tags
        should override this method.

        Parameters
        ----------
        dataset_id : str
            Source-specific dataset identifier.

        Returns
        -------
        DatasetEntry or None
            Full metadata entry, or None if not available.
        """
        return None

    @abstractmethod
    def download_dataset(self, dataset_id: str, temp_path: str) -> tuple[str, str]:
        """Download the full dataset to a local directory.

        Parameters
        ----------
        dataset_id : str
            Source-specific dataset identifier.
        temp_path : str
            Local directory path to download into.

        Returns
        -------
        tuple[str, str]
            ``(local_file_path, dataloader_name)`` — path to the downloaded
            file and the DashAI DataLoader class name to use for loading it.
        """
        ...

    @abstractmethod
    def get_download_url(self, dataset_id: str) -> str:
        """Return a direct URL the browser can use to download the dataset.

        Parameters
        ----------
        dataset_id : str
            Source-specific dataset identifier.

        Returns
        -------
        str
            Direct download URL.
        """
        ...
