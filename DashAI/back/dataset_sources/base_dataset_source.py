"""Base classes for DashAI dataset sources."""

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.utils import MultilingualString

if TYPE_CHECKING:
    import pandas as pd


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


class BaseDatasetSource(ConfigObject):
    """Abstract base class for all DashAI dataset sources.

    Subclasses connect to external dataset repositories (HuggingFace Hub,
    OpenML, Kaggle, etc.) and expose a uniform interface for searching,
    previewing, and downloading datasets.
    """

    TYPE: Final[str] = "DatasetSource"
    DISPLAY_NAME: Final = MultilingualString(en="", es="")
    DESCRIPTION: Final = MultilingualString(en="", es="")

    @abstractmethod
    def search(self, query: str, limit: int = 20, **filters: Any) -> list[DatasetEntry]:
        """Return datasets matching a query string.

        Parameters
        ----------
        query : str
            Free-text search string.
        limit : int, optional
            Maximum number of results, by default 20.
        **filters : Any
            Source-specific filter keyword arguments.

        Returns
        -------
        list[DatasetEntry]
            Matching datasets from this source.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_preview(self, dataset_id: str, n_rows: int = 100) -> "pd.DataFrame":
        """Download a sample of rows without fetching the full dataset.

        Parameters
        ----------
        dataset_id : str
            Source-specific dataset identifier.
        n_rows : int, optional
            Number of sample rows to retrieve, by default 100.

        Returns
        -------
        pd.DataFrame
            Sample rows as a pandas DataFrame.
        """
        raise NotImplementedError

    @abstractmethod
    def fetch_full(self, dataset_id: str, temp_path: str) -> tuple[str, str]:
        """Download the full dataset to a local temp directory.

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
        raise NotImplementedError

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
        raise NotImplementedError
