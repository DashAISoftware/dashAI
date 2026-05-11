"""HuggingFace Hub dataset source for DashAI."""

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Final

import httpx

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataset_sources.base_dataset_source import (
    BaseDatasetSource,
    DatasetEntry,
)

log = logging.getLogger(__name__)

_HF_API = "https://huggingface.co/api/datasets"


def _fetch_hf_treesize(dataset_id: str) -> tuple[str, int | None]:
    """Fetch total repository size for a HuggingFace dataset via the treesize API.

    Parameters
    ----------
    dataset_id : str
        HuggingFace dataset identifier in ``"namespace/repo"`` form.

    Returns
    -------
    tuple[str, int | None]
        ``(dataset_id, size_in_bytes)`` — size is None on any error.
    """
    if "/" not in dataset_id:
        return dataset_id, None
    try:
        namespace, repo = dataset_id.split("/", 1)
        resp = httpx.get(
            f"{_HF_API}/{namespace}/{repo}/treesize/main",
            timeout=5,
        )
        if resp.status_code == 200:
            raw = resp.json().get("size")
            if raw is not None:
                return dataset_id, int(raw)
    except Exception:
        log.debug("Could not fetch treesize for %s", dataset_id)
    return dataset_id, None


class HuggingFaceDatasetSource(BaseDatasetSource):
    """Dataset source that fetches public datasets from HuggingFace Hub.

    Uses the HuggingFace public REST API — no authentication required for
    public datasets.
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
        self, query: str, limit: int = 20, offset: int = 0, **filters: Any
    ) -> list[DatasetEntry]:
        """Return public HuggingFace datasets matching a query.

        Parameters
        ----------
        query : str
            Search string passed to the HuggingFace datasets API.
        limit : int, optional
            Maximum number of results, by default 20.
        offset : int, optional
            Number of results to skip (for pagination), by default 0.
        **filters : Any
            Unused; reserved for future tag/task filters.

        Returns
        -------
        list[DatasetEntry]
            Matching datasets. Returns empty list on API error.
        """
        try:
            resp = httpx.get(
                _HF_API,
                params={
                    "search": query,
                    "limit": limit,
                    "offset": offset,
                    "full": "True",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                log.warning("HuggingFace API returned %s", resp.status_code)
                return []

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

            if entries:
                max_workers = min(len(entries), 10)
                with ThreadPoolExecutor(max_workers=max_workers) as pool:
                    futures = {
                        pool.submit(_fetch_hf_treesize, e.id): e for e in entries
                    }
                    for future in as_completed(futures):
                        _, size = future.result()
                        futures[future].size_bytes = size

            return entries
        except Exception:
            log.exception("Error searching HuggingFace datasets")
            return []

    def download_dataset(self, dataset_id: str, temp_path: str) -> str:
        """Download the full dataset using the HuggingFace datasets library.

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
        from datasets import load_dataset as hf_load

        dataset = hf_load(dataset_id, cache_dir=temp_path, trust_remote_code=False)
        split = "train" if "train" in dataset else list(dataset.keys())[0]
        dataset_df = dataset[split].to_pandas()

        out_path = os.path.join(temp_path, f"{dataset_id.replace('/', '_')}.csv")
        dataset_df.to_csv(out_path, index=False)
        return out_path
