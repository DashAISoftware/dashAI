"""OpenML dataset source for DashAI."""

import io
import logging
import os
from typing import Any, Final

import httpx

from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataset_sources.base_dataset_source import BaseDatasetSource, DatasetEntry

log = logging.getLogger(__name__)

_OPENML_API = "https://www.openml.org/api/v1/json"
_OPENML_DATA = "https://data.openml.org/data/v1/download"


def _parse_quality(qualities: list[dict], name: str) -> int | None:
    """Extract a numeric quality value by name from an OpenML quality list.

    Parameters
    ----------
    qualities : list[dict]
        List of ``{"name": str, "value": str}`` dicts from OpenML API.
    name : str
        Quality name to look up (e.g. ``"NumberOfInstances"``).

    Returns
    -------
    int or None
        Parsed integer value, or None if not found or not numeric.
    """
    for q in qualities:
        if q.get("name") == name:
            try:
                return int(float(q["value"]))
            except (ValueError, KeyError):
                return None
    return None


class OpenMLDatasetSource(BaseDatasetSource):
    """Dataset source that fetches public datasets from OpenML.

    Uses the OpenML public REST API — no authentication required.
    """

    DISPLAY_NAME: Final = MultilingualString(
        en="OpenML",
        es="OpenML",
    )
    DESCRIPTION: Final = MultilingualString(
        en="Browse and import public datasets from OpenML.",
        es="Navega e importa datasets públicos desde OpenML.",
    )

    def search(self, query: str, limit: int = 20, **filters: Any) -> list[DatasetEntry]:
        """Return active OpenML datasets matching a name query.

        Parameters
        ----------
        query : str
            Dataset name search string.
        limit : int, optional
            Maximum number of results, by default 20.
        **filters : Any
            Unused; reserved for future filters.

        Returns
        -------
        list[DatasetEntry]
            Matching datasets. Returns empty list on API error.
        """
        try:
            resp = httpx.get(
                f"{_OPENML_API}/data/list",
                params={"data_name": query, "limit": limit, "status": "active"},
                timeout=15,
            )
            if resp.status_code != 200:
                log.warning("OpenML API returned %s", resp.status_code)
                return []

            items = resp.json().get("data", {}).get("dataset", [])
            entries = []
            for item in items:
                did = str(item.get("did", ""))
                qualities = item.get("quality", [])
                tag_raw = item.get("tag", [])
                tags = [tag_raw] if isinstance(tag_raw, str) else tag_raw
                entries.append(
                    DatasetEntry(
                        id=did,
                        name=item.get("name", ""),
                        description=item.get("description") or "",
                        tags=tags,
                        size_bytes=None,
                        row_count=_parse_quality(qualities, "NumberOfInstances"),
                        url=f"https://www.openml.org/d/{did}",
                        source=self.__class__.__name__,
                    )
                )
            return entries
        except Exception:
            log.exception("Error searching OpenML datasets")
            return []

    def fetch_preview(self, dataset_id: str, n_rows: int = 100) -> "pd.DataFrame":
        """Download and parse sample rows from an OpenML dataset ARFF file.

        Parameters
        ----------
        dataset_id : str
            OpenML dataset ID (integer as string, e.g. ``"61"``).
        n_rows : int, optional
            Maximum rows to return, by default 100.

        Returns
        -------
        pd.DataFrame
            Sample rows. Returns empty DataFrame on error.
        """
        import pandas as pd
        from scipy.io import arff as scipy_arff

        try:
            info_resp = httpx.get(
                f"{_OPENML_API}/data/{dataset_id}",
                timeout=15,
            )
            if info_resp.status_code != 200:
                return pd.DataFrame()

            file_id = info_resp.json()["data_set_description"]["file_id"]
            file_resp = httpx.get(
                f"{_OPENML_DATA}/{file_id}",
                timeout=60,
            )
            if file_resp.status_code != 200:
                return pd.DataFrame()

            arff_text = file_resp.content.decode("utf-8", errors="replace")
            data, meta = scipy_arff.loadarff(io.StringIO(arff_text))
            df = pd.DataFrame(data)
            for col in df.select_dtypes(include=["object"]).columns:
                df[col] = df[col].str.decode("utf-8", errors="replace")
            return df.head(n_rows)
        except Exception:
            log.exception("Error fetching OpenML preview for dataset %s", dataset_id)
            return pd.DataFrame()

    def fetch_full(self, dataset_id: str, temp_path: str) -> tuple[str, str]:
        """Download the full OpenML dataset as CSV.

        Parameters
        ----------
        dataset_id : str
            OpenML dataset ID (integer as string, e.g. ``"61"``).
        temp_path : str
            Local directory to download into.

        Returns
        -------
        tuple[str, str]
            ``(csv_file_path, "CSVDataLoader")``.
        """
        import pandas as pd
        from scipy.io import arff as scipy_arff

        info_resp = httpx.get(f"{_OPENML_API}/data/{dataset_id}", timeout=15)
        info_resp.raise_for_status()
        file_id = info_resp.json()["data_set_description"]["file_id"]

        file_resp = httpx.get(f"{_OPENML_DATA}/{file_id}", timeout=120)
        file_resp.raise_for_status()

        arff_text = file_resp.content.decode("utf-8", errors="replace")
        data, _ = scipy_arff.loadarff(io.StringIO(arff_text))
        df = pd.DataFrame(data)
        for col in df.select_dtypes(include=["object"]).columns:
            df[col] = df[col].str.decode("utf-8", errors="replace")

        out_path = os.path.join(temp_path, f"openml_{dataset_id}.csv")
        df.to_csv(out_path, index=False)
        return (out_path, "CSVDataLoader")

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
