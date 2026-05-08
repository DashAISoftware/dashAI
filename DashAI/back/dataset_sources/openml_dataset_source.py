"""OpenML dataset source for DashAI."""

import contextlib
import logging
import os
from typing import Any, Final

import httpx

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataset_sources.base_dataset_source import (
    BaseDatasetSource,
    DatasetEntry,
)

log = logging.getLogger(__name__)

_OPENML_API = "https://www.openml.org/api/v1/json"
_OPENML_ES = "https://www.openml.org/es/data/data/_search"


def _fetch_openml_details(dataset_id: str) -> dict:
    """Fetch description and tags for a single OpenML dataset.

    Parameters
    ----------
    dataset_id : str
        OpenML dataset ID (integer as string).

    Returns
    -------
    dict
        ``{"description": str, "tags": list[str]}`` — empty strings/lists on error.
    """
    try:
        resp = httpx.get(f"{_OPENML_API}/data/{dataset_id}", timeout=10)
        if resp.status_code == 200:
            desc = resp.json()["data_set_description"]
            tag_raw = desc.get("tag", [])
            return {
                "description": desc.get("description") or "",
                "tags": [tag_raw] if isinstance(tag_raw, str) else (tag_raw or []),
            }
    except Exception:
        log.debug("Could not fetch details for OpenML dataset %s", dataset_id)
    return {"description": "", "tags": []}


class OpenMLDatasetSource(BaseDatasetSource):
    """Dataset source that fetches public datasets from OpenML.

    Uses the OpenML Elasticsearch API — no authentication required.
    """

    DISPLAY_NAME: Final = MultilingualString(
        en="OpenML",
        es="OpenML",
    )
    DESCRIPTION: Final = MultilingualString(
        en="Browse and import public datasets from OpenML.",
        es="Navega e importa datasets públicos desde OpenML.",
    )

    def search(
        self, query: str, limit: int = 20, offset: int = 0, **filters: Any
    ) -> list[DatasetEntry]:
        """Return active OpenML datasets matching a name query.

        Parameters
        ----------
        query : str
            Dataset name search string.
        limit : int, optional
            Maximum number of results, by default 20.
        offset : int, optional
            Number of results to skip (for pagination), by default 0.
        **filters : Any
            Unused; reserved for future filters.

        Returns
        -------
        list[DatasetEntry]
            Matching datasets, including descriptions from the ES response.
            Returns empty list on API error.
        """
        try:
            must_clause: dict[str, Any] = (
                {"multi_match": {"query": query, "fields": ["name^3", "description"]}}
                if query
                else {"match_all": {}}
            )
            body: dict[str, Any] = {
                "from": offset,
                "size": limit,
                "query": {
                    "bool": {
                        "must": must_clause,
                        "filter": [{"term": {"status": "active"}}],
                        "should": [{"term": {"visibility": "public"}}],
                        "minimum_should_match": 1,
                    }
                },
                "_source": [
                    "data_id",
                    "name",
                    "description",
                    "qualities.NumberOfInstances",
                    "tag",
                    "status",
                ],
                "sort": {"runs": {"order": "desc"}},
            }
            resp = httpx.post(
                _OPENML_ES,
                params={"type": "data"},
                json=body,
                timeout=15,
            )
            if resp.status_code != 200:
                log.warning("OpenML ES API returned %s", resp.status_code)
                return []

            hits = resp.json().get("hits", {}).get("hits", [])
            entries = []
            for hit in hits:
                src = hit.get("_source", {})
                did = str(src.get("data_id", ""))
                tag_raw = src.get("tag", [])
                tags = [tag_raw] if isinstance(tag_raw, str) else list(tag_raw or [])
                row_count: int | None = None
                qualities = src.get("qualities", {})
                if qualities.get("NumberOfInstances") is not None:
                    with contextlib.suppress(ValueError, TypeError):
                        row_count = int(float(qualities["NumberOfInstances"]))
                entries.append(
                    DatasetEntry(
                        id=did,
                        name=src.get("name", ""),
                        description=src.get("description", "") or "",
                        tags=tags,
                        size_bytes=None,
                        row_count=row_count,
                        url=f"https://www.openml.org/d/{did}",
                        source=self.__class__.__name__,
                    )
                )
            return entries
        except Exception:
            log.exception("Error searching OpenML datasets")
            return []

    def get_info(self, dataset_id: str) -> "DatasetEntry | None":
        """Return full metadata for a single OpenML dataset (description + tags).

        Parameters
        ----------
        dataset_id : str
            OpenML dataset ID (integer as string).

        Returns
        -------
        DatasetEntry or None
            Full metadata, or None on error.
        """
        details = _fetch_openml_details(dataset_id)
        if not details["description"] and not details["tags"]:
            return None
        return DatasetEntry(
            id=dataset_id,
            name="",
            description=details["description"],
            tags=details["tags"],
            size_bytes=None,
            row_count=None,
            url=f"https://www.openml.org/d/{dataset_id}",
            source=self.__class__.__name__,
        )

    def download_dataset(self, dataset_id: str, temp_path: str) -> tuple[str, str]:
        """Download the raw ARFF file for an OpenML dataset.

        Parameters
        ----------
        dataset_id : str
            OpenML dataset ID (integer as string, e.g. ``"61"``).
        temp_path : str
            Local directory to download into.

        Returns
        -------
        tuple[str, str]
            ``(arff_file_path, "ARFFDataLoader")``.
        """
        info_resp = httpx.get(f"{_OPENML_API}/data/{dataset_id}", timeout=15)
        info_resp.raise_for_status()
        arff_url = info_resp.json()["data_set_description"]["url"]

        file_resp = httpx.get(arff_url, timeout=120, follow_redirects=True)
        file_resp.raise_for_status()

        out_path = os.path.join(temp_path, f"openml_{dataset_id}.arff")
        with open(out_path, "wb") as f:
            f.write(file_resp.content)
        return (out_path, "ARFFDataLoader")

    def get_download_url(self, dataset_id: str) -> str:
        """Return the OpenML dataset page URL.

        Parameters
        ----------
        dataset_id : str
            OpenML dataset ID.

        Returns
        -------
        str
            URL to the dataset page on openml.org.
        """
        return f"https://www.openml.org/d/{dataset_id}"
