"""HuggingFace Hub dataset source for DashAI."""

import logging
import os
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
        """Download the full dataset using the HuggingFace datasets library.

        For multi-config datasets, all configs are downloaded and concatenated
        into a single CSV file.

        Parameters
        ----------
        dataset_id : str
            HuggingFace dataset identifier (e.g. ``"stanfordnlp/imdb"``).
        temp_path : str
            Local directory to download into.

        Returns
        -------
        str
            Path to the exported CSV file inside ``temp_path``.
        """
        import pandas as pd
        from datasets import get_dataset_config_names
        from datasets import load_dataset as hf_load

        def _load_split(ds) -> pd.DataFrame:
            split = "train" if "train" in ds else list(ds.keys())[0]
            return ds[split].to_pandas()

        out_path = os.path.join(temp_path, f"{dataset_id.replace('/', '_')}.csv")

        try:
            dataset = hf_load(dataset_id, cache_dir=temp_path, trust_remote_code=False)
            _load_split(dataset).to_csv(out_path, index=False)
            return out_path
        except ValueError as exc:
            if "Config name is missing" not in str(exc):
                raise RuntimeError(
                    f"Cannot load dataset '{dataset_id}': {exc}"
                ) from exc

        configs = get_dataset_config_names(dataset_id)
        log.debug("%s has %d configs, downloading all", dataset_id, len(configs))
        dfs = []
        for config in configs:
            try:
                ds = hf_load(
                    dataset_id,
                    config,
                    cache_dir=temp_path,
                    trust_remote_code=False,
                )
                dfs.append(_load_split(ds))
            except Exception:
                log.warning(
                    "Skipping config '%s' for %s — could not load",
                    config,
                    dataset_id,
                )

        if not dfs:
            raise RuntimeError(
                f"No configs could be loaded for dataset '{dataset_id}'."
            )

        pd.concat(dfs, ignore_index=True).to_csv(out_path, index=False)
        return out_path
