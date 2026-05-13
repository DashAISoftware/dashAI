"""HuggingFace Hub dataset source for DashAI."""

import logging
import re
from typing import Any, Final
from urllib.parse import parse_qs, urlparse

import httpx

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataset_sources.base_dataset_source import (
    BaseDatasetSource,
    DatasetEntry,
    SearchPage,
)

log = logging.getLogger(__name__)

_HF_API = "https://huggingface.co/api/datasets"


def _extract_next_cursor(link_header: str) -> str | None:
    """Extract the cursor value from a HuggingFace Link response header.

    Parameters
    ----------
    link_header : str
        Value of the ``Link`` HTTP response header.

    Returns
    -------
    str or None
        The cursor token, or ``None`` if no next page is indicated.
    """
    match = re.search(r'<([^>]+)>;\s*rel="next"', link_header)
    if not match:
        return None
    params = parse_qs(urlparse(match.group(1)).query)
    cursors = params.get("cursor", [])
    return cursors[0] if cursors else None


class HuggingFaceDatasetSource(BaseDatasetSource):
    """Dataset source that fetches public datasets from HuggingFace Hub.

    Uses the HuggingFace public REST API — no authentication required for
    public datasets.  Pagination is cursor-based (the HF API ignores numeric
    offsets); the cursor is extracted from the ``Link`` response header.
    """

    DISPLAY_NAME: Final = MultilingualString(
        en="HuggingFace Hub",
        es="HuggingFace Hub",
    )
    DESCRIPTION: Final = MultilingualString(
        en="Browse and import public datasets from HuggingFace Hub.",
        es="Navega e importa datasets públicos desde HuggingFace Hub.",
    )

    def search(
        self,
        query: str,
        limit: int = 20,
        cursor: str | None = None,
        **filters: Any,
    ) -> SearchPage:
        """Return public HuggingFace datasets matching a query.

        Parameters
        ----------
        query : str
            Search string passed to the HuggingFace datasets API.
        limit : int, optional
            Maximum number of results, by default 20.
        cursor : str or None, optional
            Pagination cursor returned by the previous call.  ``None`` fetches
            the first page.
        **filters : Any
            Unused; reserved for future tag/task filters.

        Returns
        -------
        SearchPage
            Matching datasets and cursor for the next page (or ``None``).
        """
        try:
            params: dict[str, Any] = {
                "search": query,
                "limit": limit,
                "full": "True",
            }
            if cursor:
                params["cursor"] = cursor

            resp = httpx.get(_HF_API, params=params, timeout=15)
            if resp.status_code != 200:
                log.warning("HuggingFace API returned %s", resp.status_code)
                return SearchPage()

            next_cursor = _extract_next_cursor(resp.headers.get("Link", ""))

            entries = [
                DatasetEntry(
                    id=item.get("id", ""),
                    name=item.get("id", "").split("/")[-1],
                    description=item.get("description") or "",
                    tags=item.get("tags", []),
                    size_bytes=None,
                    url=f"https://huggingface.co/datasets/{item.get('id', '')}",
                    source=self.__class__.__name__,
                )
                for item in resp.json()
            ]

            return SearchPage(entries=entries, next_cursor=next_cursor)
        except Exception:
            log.exception("Error searching HuggingFace datasets")
            return SearchPage()

    def get_info(self, dataset_id: str) -> "DatasetEntry | None":
        """Return full metadata for a single HuggingFace dataset, including size.

        Parameters
        ----------
        dataset_id : str
            HuggingFace dataset identifier in ``"namespace/repo"`` form.

        Returns
        -------
        DatasetEntry or None
            Full metadata entry, or None on error.
        """
        try:
            from huggingface_hub import HfApi

            item = HfApi().dataset_info(dataset_id)
            return DatasetEntry(
                id=dataset_id,
                name=dataset_id.split("/")[-1],
                description=item.description or "",
                tags=list(item.tags or []),
                size_bytes=item.used_storage,
                url=f"https://huggingface.co/datasets/{dataset_id}",
                source=self.__class__.__name__,
            )
        except Exception:
            log.debug("Could not fetch info for HuggingFace dataset %s", dataset_id)
            return None

    def download_dataset(self, dataset_id: str, temp_path: str) -> str:
        """Download the raw dataset files from HuggingFace Hub.

        Parameters
        ----------
        dataset_id : str
            HuggingFace dataset identifier (e.g. ``"stanfordnlp/imdb"``).
        temp_path : str
            Local directory to download into.

        Returns
        -------
        str
            Path to the directory containing the downloaded files.
        """
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=dataset_id,
            repo_type="dataset",
            local_dir=temp_path,
            ignore_patterns=["*.md", "*.gitattributes", ".gitattributes"],
        )
        return temp_path
