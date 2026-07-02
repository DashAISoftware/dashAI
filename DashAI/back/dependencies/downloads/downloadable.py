"""Source-agnostic mixin for components that download external artifacts.

Each downloadable component owns a directory ``<COMPONENT_PATH>/<ClassName>`` and
is responsible for downloading its artifacts into that directory and removing
them from it. There is no shared cache; ``HFDownloadableMixin`` covers the common
HuggingFace case by downloading each repo into the component's own folder.
"""

import logging
import pathlib
import shutil
from typing import Callable, List, Optional, Tuple, Union

from huggingface_hub import snapshot_download
from kink import di

logger = logging.getLogger(__name__)

# report(fraction, message): fraction in [0, 1] or None for indeterminate.
ProgressReporter = Callable[[Optional[float], Optional[str]], None]


def _components_root() -> pathlib.Path:
    """Return the base directory that holds one folder per component."""
    return pathlib.Path(di["config"]["COMPONENT_PATH"])


class DownloadableMixin:
    """Marks a component as requiring an explicit download.

    Subclasses implement ``is_downloaded`` and ``download`` for their own source
    and store artifacts under ``component_dir()``. ``delete`` defaults to removing
    that directory. See ``HFDownloadableMixin`` for the HuggingFace case.
    """

    REQUIRES_DOWNLOAD: bool = True
    DOWNLOAD_SIZE_BYTES: Optional[int] = None

    @classmethod
    def component_dir(cls) -> pathlib.Path:
        """Return this component's own storage directory.

        Returns
        -------
        pathlib.Path
            ``<COMPONENT_PATH>/<ClassName>``.
        """
        return _components_root() / cls.__name__

    @classmethod
    def is_downloaded(cls) -> bool:
        """Return whether the component's artifacts are present locally."""
        raise NotImplementedError

    @classmethod
    def download(cls, report: Optional[ProgressReporter] = None) -> None:
        """Fetch the component's artifacts into ``component_dir()``."""
        raise NotImplementedError

    @classmethod
    def delete(cls) -> None:
        """Remove the component's downloaded artifacts."""
        shutil.rmtree(cls.component_dir(), ignore_errors=True)


class HFDownloadableMixin(DownloadableMixin):
    """Downloadable component whose artifacts are HuggingFace repos.

    Each repo is downloaded into ``component_dir()/<repo-leaf>``. Subclasses set
    ``HF_REPOS`` or, for a dynamic repo (e.g. derived from a per-subclass
    ``MODEL_NAME``), override ``hf_repos``.

    ``HF_REPOS`` entries accept two shapes:

    * ``(repo_id, repo_type)`` -- full snapshot download (original behavior).
    * ``(repo_id, repo_type, allow_patterns)`` -- partial download; only files
      matching the glob patterns in ``allow_patterns`` are fetched.
    """

    HF_REPOS: List[Union[Tuple[str, str], Tuple[str, str, List[str]]]] = []

    @classmethod
    def hf_repos(cls) -> List[Union[Tuple[str, str], Tuple[str, str, List[str]]]]:
        """Return the repo entries this component needs.

        Returns
        -------
        list of tuple
            Each entry is either ``(repo_id, repo_type)`` or
            ``(repo_id, repo_type, allow_patterns)``.
        """
        return list(cls.HF_REPOS)

    @classmethod
    def _unpack_entry(
        cls,
        entry: Union[Tuple[str, str], Tuple[str, str, List[str]]],
    ) -> Tuple[str, str, Optional[List[str]]]:
        """Normalise a repo entry into ``(repo_id, repo_type, allow_patterns)``.
        Parameters
        ----------
        entry : tuple
            Either a 2-tuple ``(repo_id, repo_type)`` or a 3-tuple
            ``(repo_id, repo_type, allow_patterns)``.

        Returns
        -------
        tuple of (str, str, list[str] or None)
            ``repo_id``, ``repo_type``, and ``allow_patterns`` (``None`` when
            the entry was a 2-tuple, meaning a full snapshot download).

        Raises
        ------
        ValueError
            If ``entry`` has a length other than 2 or 3.
        """
        if len(entry) == 2:
            rid, rtype = entry
            return rid, rtype, None
        if len(entry) == 3:
            rid, rtype, patterns = entry
            return rid, rtype, patterns
        raise ValueError(
            f"HF_REPOS entries must be 2- or 3-tuples; "
            f"got length {len(entry)}: {entry!r}"
        )

    @classmethod
    def _repo_dir(cls, repo_id: str) -> pathlib.Path:
        """Return the local directory for a single repo under component_dir().

        Parameters
        ----------
        repo_id : str
            HuggingFace repo identifier, e.g. ``"owner/model-name"``.

        Returns
        -------
        pathlib.Path
            ``component_dir()/<repo-leaf>``.
        """
        return cls.component_dir() / repo_id.split("/")[-1]

    @classmethod
    def is_downloaded(cls) -> bool:
        """Return whether all repo directories exist and are non-empty.

        Returns
        -------
        bool
            ``True`` when every repo listed in ``hf_repos()`` has a non-empty
            local directory; ``False`` otherwise (including when the list is
            empty).
        """
        repos = cls.hf_repos()
        return bool(repos) and all(
            cls._repo_dir(rid).is_dir() and any(cls._repo_dir(rid).iterdir())
            for rid, *_ in repos
        )

    @classmethod
    def download(cls, report: Optional[ProgressReporter] = None) -> None:
        """Download all repos listed in ``hf_repos()`` into ``component_dir()``.

        Parameters
        ----------
        report : ProgressReporter, optional
            Callback invoked before each repo download with
            ``report(None, "Downloading <repo_id>")``.  ``None`` means no
            progress reporting.
        """
        for entry in cls.hf_repos():
            rid, rtype, allow_patterns = cls._unpack_entry(entry)
            target = cls._repo_dir(rid)
            target.mkdir(parents=True, exist_ok=True)
            if report is not None:
                # snapshot_download exposes no aggregate byte count, so progress
                # is reported as indeterminate (None) with a phase message.
                report(None, f"Downloading {rid}")
            kwargs = {}
            if allow_patterns is not None:
                kwargs["allow_patterns"] = allow_patterns
            snapshot_download(
                repo_id=rid, repo_type=rtype, local_dir=str(target), **kwargs
            )
