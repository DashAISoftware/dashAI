import functools
import gzip
import hashlib
import io
import json
import logging
import re
import shutil
import tarfile
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from urllib.parse import quote, unquote

import httpx

from DashAI.back.plugins.sources.base import (
    Fetched,
    NotFoundError,
    RateLimitError,
    SourceError,
    TrustLevel,
    TrustTier,
    check_size,
)
from DashAI.back.plugins.sources.local_source import _extract_zip, _resolve_plugin_root

# GitHub owners (lowercase) whose plugins are ``verified``.
_OFFICIAL_OWNERS = frozenset({"dashaisoftware"})


def is_official(owner: str) -> bool:
    """Published by DashAISoftware, judged by the URL's owner, not the manifest."""
    return owner.lower() in _OFFICIAL_OWNERS


# A release file signed by the repo's own CI at that tag (sigstore)
GITHUB_ATTESTED = TrustLevel("github_attested", TrustTier.ATTESTED)
# No release file. The repo's code, downloaded by the tag's commit SHA.
GITHUB_SOURCE = TrustLevel("github_source", TrustTier.SOURCE)
# A release file without valid attestation, its digest only catches corruption
GITHUB_ASSET = TrustLevel("github_asset", TrustTier.UNVERIFIED)

_GITHUB_URL = re.compile(
    r"^https://(?:www\.)?github\.com/([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+?)(?:\.git)?/?$"
)

_ASSET_EXTENSIONS = (".zip", ".tar.gz")

_API = "https://api.github.com/"
_REPO_PATH = re.compile(r"^/repos/([^/]+)/([^/]+)/")

_LATEST_TAG_TIMEOUT_SECONDS = 5

# Retries for transient attestation failures (network, 5xx, TUF refresh).
_ATTESTATION_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 1.0

_ACTIONS_ISSUER = "https://token.actions.githubusercontent.com"

logger = logging.getLogger(__name__)


def _backoff(attempt: int) -> None:
    time.sleep(_RETRY_BACKOFF_SECONDS * 2**attempt)


@functools.lru_cache(maxsize=1)
def _production_verifier():
    # Built on first use and not cached on failure, as it fetches the trust root
    from sigstore.verify import Verifier

    for attempt in range(_ATTESTATION_ATTEMPTS):
        try:
            return Verifier.production()
        except Exception as error:  # noqa: BLE001
            if attempt == _ATTESTATION_ATTEMPTS - 1:
                raise
            logger.info(
                "Sigstore trust root refresh failed (attempt %d/%d): %s",
                attempt + 1,
                _ATTESTATION_ATTEMPTS,
                error,
            )
            _backoff(attempt)
    raise AssertionError("unreachable")


def _verify_with_sigstore(
    bundle: Dict[str, Any], repo_uri: str, ref: str, workflow: Optional[str] = None
) -> bytes:
    """In-toto statement of a bundle by ``repo_uri``'s CI at ``ref``, or raise."""
    from sigstore.models import Bundle
    from sigstore.verify import policy

    policies = [
        policy.OIDCIssuerV2(_ACTIONS_ISSUER),
        policy.OIDCSourceRepositoryURI(repo_uri),
        policy.OIDCSourceRepositoryRef(ref),
        policy.OIDCRunnerEnvironment("github-hosted"),
    ]
    if workflow:
        policies.append(policy.OIDCBuildConfigURI(workflow))
    _payload_type, payload = _production_verifier().verify_dsse(
        Bundle.from_json(json.dumps(bundle)), policy.AllOf(policies)
    )
    return payload


def _attestation_details(
    bundle: Dict[str, Any], statement: Dict[str, Any]
) -> Dict[str, Optional[str]]:
    """An attestation's commit, workflow and signing time."""
    try:
        parameters = statement["predicate"]["buildDefinition"]["externalParameters"]
        workflow = parameters["workflow"]["path"]
    except (KeyError, TypeError):
        workflow = None
    try:
        entry = bundle["verificationMaterial"]["tlogEntries"][0]
        signed_at = datetime.fromtimestamp(
            int(entry["integratedTime"]), timezone.utc
        ).isoformat()
    except (KeyError, IndexError, TypeError, ValueError):
        signed_at = None
    return {
        "commit": _attested_commit(statement),
        "workflow": workflow,
        "signed_at": signed_at,
    }


def _attested_commit(statement: Dict[str, Any]) -> Optional[str]:
    """The commit a SLSA provenance statement says the build ran on, if any."""
    try:
        dependencies = statement["predicate"]["buildDefinition"]["resolvedDependencies"]
        return next(
            dep["digest"]["gitCommit"]
            for dep in dependencies
            if "gitCommit" in dep.get("digest", {})
        )
    except (KeyError, TypeError, StopIteration):
        return None


class GitHubSourceError(SourceError):
    """A plugin could not be fetched from GitHub."""


class GitHubRateLimitError(GitHubSourceError, RateLimitError):
    """GitHub's rate limit is exhausted."""

    code = "rate_limited"


class GitHubNotFoundError(GitHubSourceError, NotFoundError):
    """The repo, or a published release of it, does not exist (or is private)."""

    code = "not_found"


def _single_root(folder: Path) -> Path:
    entries = list(folder.iterdir())
    dirs = [child for child in entries if child.is_dir()]
    if len(dirs) != 1 or len(entries) != len(dirs):
        raise GitHubSourceError(
            "Expected a single top-level directory in the tarball, found: "
            f"{[entry.name for entry in entries]}",
            "invalid_archive",
        )
    return dirs[0]


@contextmanager
def _extract_tarball(
    blob: bytes, root_of: Callable[[Path], Path], context: str
) -> Iterator[Path]:
    """Extract to a temp dir (removed after); yield ``root_of`` the tree."""
    tmp = Path(tempfile.mkdtemp(prefix="dashai-plugin-"))
    try:
        try:
            with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
                check_size(sum(m.size for m in tar.getmembers()), context)
                tar.extractall(tmp, filter="data")
        except (tarfile.TarError, OSError) as error:
            raise GitHubSourceError(
                f"Could not extract {context}: {error}", "invalid_archive"
            ) from error
        root = root_of(tmp)
        if not (root / "manifest.json").is_file():
            raise GitHubSourceError(
                f"manifest.json not found in {context}", "manifest_not_found"
            )
        yield root
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _tar_digest(blob: bytes) -> str:
    """sha256 of the uncompressed tar, stable across GitHub's recompressions."""
    digest = hashlib.sha256()
    with gzip.GzipFile(fileobj=io.BytesIO(blob)) as tar:
        while chunk := tar.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _same_digest(actual: str, expected: str, what: str) -> None:
    if actual != expected:
        raise GitHubSourceError(
            f"{what} hashes to {actual}, not the reviewed {expected}", "digest_mismatch"
        )


def _path_segment(tag: str) -> str:
    """A tag as one URL path segment, so it can't reach other API paths."""
    if tag in ("", ".", ".."):
        raise GitHubSourceError(f"Invalid tag: {tag!r}", "tag_not_found", tag=tag)
    return quote(tag, safe="")


@contextmanager
def _extract_asset(name: str, blob: bytes) -> Iterator[Path]:
    if name.lower().endswith(".zip"):
        with _extract_zip(io.BytesIO(blob)) as root:
            yield root
        return
    context = f"asset '{name}'"
    with _extract_tarball(blob, _resolve_plugin_root, context) as root:
        yield root


def _ok(response: httpx.Response, failed: str) -> httpx.Response:
    """``response``, or ``GitHubSourceError`` prefixed with ``failed``."""
    try:
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise GitHubSourceError(f"{failed}: {error}") from error
    return response


def _raise_if_rate_limited(response: httpx.Response, authenticated: bool) -> None:
    exhausted = response.status_code in (403, 429) and (
        response.headers.get("x-ratelimit-remaining") == "0"
        or "retry-after" in response.headers
    )
    if not exhausted:
        return
    reset = response.headers.get("x-ratelimit-reset")
    when = (
        f" It resets at {datetime.fromtimestamp(int(reset)):%H:%M}."
        if reset and reset.isdigit()
        else ""
    )
    if authenticated:
        advice = ""
    else:
        advice = (
            " Without a token GitHub allows 60 requests per hour per network;"
            " add a GitHub token in Credentials to raise it to 5,000."
        )
    raise GitHubRateLimitError(
        f"GitHub rate limit reached.{when}{advice}",
        resets_at=int(reset) if reset and reset.isdigit() else None,
        authenticated=authenticated,
    )


@dataclass
class _Release:
    owner: str  # the repo's real owner and name, after GitHub redirects
    repo: str
    tag: str
    assets: List[Dict[str, Any]] = field(default_factory=list)


class GitHubSource:
    """Plugins from GitHub releases, via the REST API or the store's index."""

    can_update = True
    trust_levels = (GITHUB_ATTESTED, GITHUB_SOURCE, GITHUB_ASSET)

    def __init__(
        self,
        client: Optional[httpx.Client] = None,
        verify_attestation: Callable[
            [Dict[str, Any], str, str], bytes
        ] = _verify_with_sigstore,
        token: Callable[[], Optional[str]] = lambda: None,
    ):
        if client is not None:
            self._client = client
        self._verify_attestation = verify_attestation
        self._token = token  # read per call, so credential changes apply at once

    @functools.cached_property
    def _client(self) -> httpx.Client:
        """Made on first use, loading its certificates takes ~0.2 s."""
        return httpx.Client(follow_redirects=True, timeout=30.0)

    @staticmethod
    @functools.lru_cache(maxsize=4096)  # the store asks each location's parts
    def parse(url: str) -> Tuple[str, str]:
        match = _GITHUB_URL.match(url.strip())
        if not match:
            raise GitHubSourceError(f"Not a GitHub repo URL: {url}", "invalid_location")
        return match.group(1), match.group(2)

    @classmethod
    def key(cls, url: str) -> Tuple[str, str]:
        """(owner, repo) in lowercase, as GitHub compares them."""
        owner, repo = cls.parse(url)
        return owner.lower(), repo.lower()

    @classmethod
    def web_url(cls, url: str, commit: Optional[str] = None) -> str:
        base = "https://github.com/{}/{}".format(*cls.parse(url))
        return f"{base}/blob/{commit}/" if commit else base

    @classmethod
    def readme_base(cls, url: str, commit: str) -> str:
        owner, repo = cls.parse(url)
        return f"https://raw.githubusercontent.com/{owner}/{repo}/{commit}/"

    @classmethod
    def owner(cls, url: str) -> str:
        return cls.parse(url)[0]

    @classmethod
    def official(cls, url: str) -> bool:
        return is_official(cls.owner(url))

    def _current_token(self) -> Optional[str]:
        try:
            return self._token()
        except Exception as error:  # noqa: BLE001
            logger.warning("Could not read the GitHub token: %s", error)
            return None

    def _request(
        self, url: str, token: Optional[str], headers: Dict[str, str], timeout
    ) -> httpx.Response:
        if token:
            headers = {**headers, "Authorization": f"Bearer {token}"}
        try:
            return self._client.get(url, headers=headers, timeout=timeout)
        except httpx.HTTPError as error:
            raise GitHubSourceError(
                f"Request failed: {url} ({error})", "offline"
            ) from error

    def _get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout=httpx.USE_CLIENT_DEFAULT,
    ) -> httpx.Response:
        # The token only goes to the REST API, never to download hosts.
        token = self._current_token() if url.startswith(_API) else None
        response = self._request(url, token, headers or {}, timeout)
        if token and response.status_code == 401:
            logger.warning("GitHub rejected the stored token; retrying without it")
            token = None
            response = self._request(url, None, headers or {}, timeout)
        _raise_if_rate_limited(response, authenticated=bool(token))
        return response

    def latest_tag(
        self, url: str, etag: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """``(tag, etag)`` of the latest release, tag None on a 304."""
        owner, repo = self.parse(url)
        response = self._get(
            f"{_API}repos/{owner}/{repo}/releases/latest",
            headers={"If-None-Match": etag} if etag else None,
            timeout=_LATEST_TAG_TIMEOUT_SECONDS,
        )
        if response.status_code == 304:
            return None, etag
        if response.status_code == 404:
            raise GitHubNotFoundError(f"No published release: {owner}/{repo}")
        data = _ok(response, "Could not read latest release").json()
        return data["tag_name"], response.headers.get("etag")

    def _fetch_release(self, owner: str, repo: str, ref: Optional[str]) -> _Release:
        full_name = f"{owner}/{repo}"
        if ref:
            url = f"{_API}repos/{owner}/{repo}/releases/tags/{_path_segment(ref)}"
            not_found = f"No release found for tag '{ref}': {full_name}"
            code = "tag_not_found"
            read_failed = f"Could not read release '{ref}'"
        else:
            url = f"{_API}repos/{owner}/{repo}/releases/latest"
            not_found = f"Repo has no published releases: {full_name}"
            code = "no_release"
            read_failed = "Could not read latest release"
        response = self._get(url)
        if response.status_code == 404:
            if self._get(f"{_API}repos/{owner}/{repo}").status_code == 404:
                not_found = (
                    f"Repo not found (private repos are not supported): {full_name}"
                )
                code = "not_found"
            raise GitHubSourceError(not_found, code, repo=full_name, tag=ref)
        data = _ok(response, read_failed).json()
        # GitHub's canonical name, the one attestations are signed for
        final = _REPO_PATH.match(httpx.URL(data.get("url") or response.url).path)
        owner, repo = final.groups() if final else (owner, repo)
        return _Release(owner, repo, data["tag_name"], data.get("assets") or [])

    def _commit_of(self, owner: str, repo: str, tag: str) -> str:
        response = self._get(f"{_API}repos/{owner}/{repo}/commits/{_path_segment(tag)}")
        try:
            response.raise_for_status()
            return response.json()["sha"]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
            raise GitHubSourceError(
                f"Could not resolve tag '{tag}' to a commit: {error}"
            ) from error

    def _download(self, url: str, what: str, size: Optional[int] = None) -> bytearray:
        """Download over https within the size limit, a reviewed ``size`` exactly."""

        def check(length: int) -> None:
            check_size(length, what)
            if size is not None and length > size:
                raise GitHubSourceError(
                    f"{what} is not the {size} bytes reviewed", "digest_mismatch"
                )

        blob = bytearray()
        try:
            with self._client.stream("GET", url) as response:
                _ok(response, f"Could not download {what}")
                hops = [*response.history, response]
                if any(hop.url.scheme != "https" for hop in hops):
                    raise GitHubSourceError(f"{what} redirected off https: {url}")
                stated = response.headers.get("content-length", "")
                if stated.isdigit():
                    check(int(stated))
                for chunk in response.iter_bytes():
                    blob += chunk
                    check(len(blob))
        except httpx.HTTPError as error:
            raise GitHubSourceError(
                f"Request failed: {url} ({error})", "offline"
            ) from error
        if size is not None and len(blob) < size:
            raise GitHubSourceError(f"Download of {what} was cut short", "offline")
        return blob

    def download_tarball(self, owner: str, repo: str, commit: str) -> bytearray:
        # By commit, since a tag can be moved and a commit can't.
        url = f"https://codeload.github.com/{owner}/{repo}/tar.gz/{commit}"
        return self._download(url, "tarball")

    def _download_asset(self, asset: Dict[str, Any]) -> bytearray:
        what = f"asset '{asset['name']}'"
        check_size(asset.get("size", 0), what)  # GitHub states it, no download
        return self._download(asset["browser_download_url"], what)

    def _verify_asset_digest(self, asset: Dict[str, Any], actual: str) -> None:
        """Fail if ``actual`` isn't GitHub's digest, when the asset has one."""
        digest = asset.get("digest") or ""
        algorithm, _, expected = digest.partition(":")
        if algorithm.lower() != "sha256" or not expected:
            return
        if actual != expected.lower():
            raise GitHubSourceError(
                f"Asset '{asset['name']}' failed digest verification: "
                f"GitHub reports {expected}, downloaded content hashes to {actual}",
                "digest_mismatch",
            )

    def _get_attestations(self, url: str) -> httpx.Response:
        """GET, retrying only connection errors and 5xx."""
        for attempt in range(_ATTESTATION_ATTEMPTS):
            last = attempt == _ATTESTATION_ATTEMPTS - 1
            try:
                response = self._get(url)
            except GitHubRateLimitError:
                raise
            except GitHubSourceError:
                if last:
                    raise
            else:
                if response.status_code < 500 or last:
                    return response
            _backoff(attempt)
        raise AssertionError("unreachable")

    def _check_attestation(
        self, owner: str, repo: str, tag: str, sha256: str
    ) -> Optional[Dict[str, Optional[str]]]:
        """``_attestation_details`` if this repo's CI built it at ``tag``, else None."""
        url = f"{_API}repos/{owner}/{repo}/attestations/sha256:{sha256}"
        try:
            response = self._get_attestations(url)
            if response.status_code != 200:
                return None
            bundles = [item["bundle"] for item in response.json()["attestations"]]
        except GitHubRateLimitError:
            raise
        except (GitHubSourceError, ValueError, KeyError, TypeError):
            return None
        return self._accepted(bundles, owner, repo, tag, sha256)

    def _accepted(
        self, bundles: List[Any], owner: str, repo: str, tag: str, sha256: str
    ) -> Optional[Dict[str, Optional[str]]]:
        """Details of the first bundle this repo's CI signed at ``tag``."""
        # Case-sensitive. A URL typed in other casing is not attested.
        repo_uri = f"https://github.com/{owner}/{repo}"
        for bundle in bundles:
            try:
                statement = json.loads(
                    self._verify_attestation(bundle, repo_uri, f"refs/tags/{tag}")
                )
                if any(
                    subject.get("digest", {}).get("sha256") == sha256
                    for subject in statement.get("subject", [])
                ):
                    return _attestation_details(bundle, statement)
            except Exception as error:  # noqa: BLE001
                logger.info(
                    "Attestation for %s/%s not accepted: %s", owner, repo, error
                )
        return None

    @staticmethod
    def _fetched(
        path: Path,
        owner: str,
        tag: str,
        sha256: str,
        *,
        asset: Optional[str],
        attestation: Optional[Dict[str, Optional[str]]],
        commit: Optional[str],
    ) -> Fetched:
        """A release file signed by the repo's CI > the repo's code > any file."""
        if attestation is not None:
            level = GITHUB_ATTESTED
        else:
            level = GITHUB_ASSET if asset else GITHUB_SOURCE
        verified = is_official(owner)
        attestation = attestation or {}
        return Fetched(
            path,
            tag,
            level.name,
            verified,
            sha256,
            attestation.get("commit", commit),
            asset=asset,
            workflow=attestation.get("workflow"),
            signed_at=attestation.get("signed_at"),
            issuer=_ACTIONS_ISSUER if level is GITHUB_ATTESTED else None,
        )

    @contextmanager
    def fetch(self, url: str, ref: Optional[str] = None) -> Iterator[Fetched]:
        release = self._fetch_release(*self.parse(url), ref)
        owner, repo = release.owner, release.repo
        candidates = [
            asset
            for asset in release.assets
            if asset.get("name", "").lower().endswith(_ASSET_EXTENSIONS)
        ]
        if len(candidates) == 1:
            blob = self._download_asset(candidates[0])
            sha256 = hashlib.sha256(blob).hexdigest()
            self._verify_asset_digest(candidates[0], sha256)
            with _extract_asset(candidates[0]["name"], blob) as path:
                # An unattested file names no commit, even if its release does.
                yield self._fetched(
                    path,
                    owner,
                    release.tag,
                    sha256,
                    asset=candidates[0]["name"],
                    attestation=self._check_attestation(
                        owner, repo, release.tag, sha256
                    ),
                    commit=None,
                )
            return

        commit = self._commit_of(owner, repo, release.tag)
        blob = self.download_tarball(owner, repo, commit)
        context = f"tarball for {owner}/{repo}@{release.tag} ({commit[:7]})"
        with _extract_tarball(blob, _single_root, context) as path:
            yield self._fetched(
                path,
                owner,
                release.tag,
                _tar_digest(blob),
                asset=None,
                attestation=None,
                commit=commit,
            )

    @contextmanager
    def fetch_listed(
        self,
        location: str,
        tag: str,
        *,
        kind: str,
        sha256: str,
        commit: str,
        url: Optional[str] = None,
        size: Optional[int] = None,
        bundle_url: Optional[str] = None,
    ) -> Iterator[Fetched]:
        """A release as the store's index lists it, without the REST API."""
        owner, repo = self.parse(location)
        if kind == "source":  # the URL is built here, never read from the index
            blob = self.download_tarball(owner, repo, commit)
            _same_digest(_tar_digest(blob), sha256, "tarball")
            context = f"tarball for {owner}/{repo}@{tag} ({commit[:7]})"
            with _extract_tarball(blob, _single_root, context) as path:
                yield self._fetched(
                    path,
                    owner,
                    tag,
                    sha256,
                    asset=None,
                    attestation=None,
                    commit=commit,
                )
            return
        # Unsigned, so only a file of that very release, hosted by GitHub.
        release = f"https://github.com/{owner}/{repo}/releases/download/"
        release += f"{_path_segment(tag)}/"
        rest = url[len(release) :]
        if not bundle_url and (
            url[: len(release)].lower() != release.lower() or not rest or "/" in rest
        ):
            raise GitHubSourceError(f"Not a file of release {tag}: {url}")
        name = unquote(httpx.URL(url).path.rsplit("/", 1)[-1])
        blob = self._download(url, f"asset '{name}'", size)
        _same_digest(hashlib.sha256(blob).hexdigest(), sha256, f"asset '{name}'")
        attestation = None
        if bundle_url:
            try:
                bundle = json.loads(self._download(bundle_url, "attestation"))
            except GitHubSourceError as error:
                cause = error.__cause__
                missing = isinstance(cause, httpx.HTTPStatusError)
                if not (missing and cause.response.status_code == 404):
                    # never unattested for a network cut
                    raise GitHubSourceError(str(error), "offline") from error
                bundle = None  # unattested
            except ValueError:
                bundle = None
            if bundle is not None:
                attestation = self._accepted([bundle], owner, repo, tag, sha256)
        with _extract_asset(name, blob) as path:
            yield self._fetched(
                path,
                owner,
                tag,
                sha256,
                asset=name,
                attestation=attestation,
                commit=None,
            )
