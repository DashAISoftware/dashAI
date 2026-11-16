import gzip
import hashlib
import io
import json
import tarfile

import httpx
import pytest
from plugin_helpers import URL, zip_bytes

from DashAI.back.plugins.sources.base import SourceError
from DashAI.back.plugins.sources.github_source import (
    GitHubRateLimitError,
    GitHubSource,
    GitHubSourceError,
)

ASSET_URL = "https://assets.example/plugin.zip"
ZIP = zip_bytes({"manifest.json": "{}"})
ZIP_SHA = hashlib.sha256(ZIP).hexdigest()


def _make_tarball(members: dict) -> bytes:
    """An in-memory .tar.gz of ``{name: bytes}``, folders implicit."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, content in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def _repo_tarball() -> bytes:
    return _make_tarball(
        {"repo-1.0.0/src/plugin.py": b"# code\n", "repo-1.0.0/manifest.json": b"{}"}
    )


def _asset(name: str, url: str, digest: str | None = None) -> dict:
    entry = {"name": name, "browser_download_url": url}
    if digest is not None:
        entry["digest"] = digest
    return entry


def _source_with_routes(routes, **kwargs) -> GitHubSource:
    """A GitHubSource whose HTTP client is served by ``routes(request)``."""
    client = httpx.Client(transport=httpx.MockTransport(routes), follow_redirects=True)
    return GitHubSource(client=client, **kwargs)


def _default_routes(tarball=None, tag="v1.0.0", calls=None, assets=(), blobs=None):
    """The release, its asset downloads (``blobs``) and the tarball fallback."""
    blobs = blobs or {}

    def routes(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if calls is not None:
            calls.append(path)
        if path.endswith("/releases/latest"):
            return httpx.Response(200, json={"tag_name": tag, "assets": list(assets)})
        if "/releases/tags/" in path:
            requested = path.rsplit("/releases/tags/", 1)[-1]
            return httpx.Response(
                200, json={"tag_name": requested, "assets": list(assets)}
            )
        if "/commits/" in path:
            return httpx.Response(
                200, json={"sha": "0123456789abcdef" * 2 + "01234567"}
            )
        if str(request.url) in blobs:
            return httpx.Response(200, content=blobs[str(request.url)])
        if "/tar.gz/" in path and tarball is not None:
            return httpx.Response(200, content=tarball)
        return httpx.Response(404)

    return routes


def _fails(source, error, match=None, ref=None):
    with pytest.raises(error, match=match), source.fetch(URL, ref=ref):
        pass


def test_a_repo_is_compared_and_linked_by_owner_and_name():
    url = "https://github.com/Acme/Kit.git"
    assert GitHubSource.key(url) == GitHubSource.key("https://github.com/acme/kit/")
    assert GitHubSource.key(url) != GitHubSource.key("https://github.com/fork/kit")
    assert GitHubSource.web_url(url) == "https://github.com/Acme/Kit"
    assert GitHubSource.web_url(url, "c1") == "https://github.com/Acme/Kit/blob/c1/"
    assert GitHubSource.readme_base(url, "c1") == (
        "https://raw.githubusercontent.com/Acme/Kit/c1/"
    )
    assert GitHubSource.owner(url) == "Acme"
    assert GitHubSource.official("https://github.com/DashAISoftware/kit")
    assert not GitHubSource.official(url)


def test_a_location_that_is_not_a_repo_is_invalid():
    with pytest.raises(SourceError) as raised:
        GitHubSource.key("https://gitlab.com/acme/kit")
    assert raised.value.code == "invalid_location"


@pytest.mark.parametrize(
    ("owner", "verified"),
    [("DashAISoftware", True), ("dashaisoftware", True), ("someone", False)],
)
def test_verified_only_for_repos_owned_by_dashai(owner, verified):
    source = _source_with_routes(_default_routes(_repo_tarball()))

    with source.fetch(f"https://github.com/{owner}/repo") as fetched:
        pass

    assert fetched.verified is verified


@pytest.mark.parametrize(
    ("with_asset", "level"), [(True, "github_asset"), (False, "github_source")]
)
def test_fetch_prefers_the_single_zip_asset_over_the_tree(with_asset, level):
    assets = [_asset("plugin.zip", ASSET_URL)] if with_asset else []
    routes = _default_routes(_repo_tarball(), assets=assets, blobs={ASSET_URL: ZIP})
    source = _source_with_routes(routes)

    with source.fetch(URL) as fetched:
        assert (fetched.path / "manifest.json").is_file()
    assert fetched.trust_level == level


def test_fetch_rejects_an_asset_with_a_mismatched_digest():
    asset = _asset("plugin.zip", ASSET_URL, digest="sha256:" + "0" * 64)
    routes = _default_routes(assets=[asset], blobs={ASSET_URL: ZIP})

    _fails(_source_with_routes(routes), GitHubSourceError, "failed digest verification")


def test_fetch_blocks_path_traversal():
    # An escaping member aborts extraction (filter=data), nothing written outside
    malicious = _make_tarball(
        {"repo-1.0.0/../../evil.txt": b"pwned", "repo-1.0.0/manifest.json": b"{}"}
    )
    source = _source_with_routes(_default_routes(malicious))

    _fails(source, GitHubSourceError, "Could not extract tarball")


def test_a_tag_stays_one_path_segment():
    paths = []

    def routes(request):
        paths.append(request.url.raw_path.decode())
        return httpx.Response(404)

    source = _source_with_routes(routes)
    _fails(source, GitHubSourceError, ref="../../../user")
    _fails(source, GitHubSourceError, "Invalid tag", ref="..")

    assert paths[0] == "/repos/owner/repo/releases/tags/..%2F..%2F..%2Fuser"


def test_the_sources_sha256_survives_github_recompressing_it():
    # GitHub recompressed .tar.gz in 2023, the hash of the inner tar still matches
    tarball = _repo_tarball()
    recompressed = gzip.compress(gzip.decompress(tarball), compresslevel=1)
    assert recompressed != tarball

    digests = []
    for blob in (tarball, recompressed):
        with _source_with_routes(_default_routes(blob)).fetch(URL) as fetched:
            digests.append(fetched.sha256)

    assert digests == [hashlib.sha256(gzip.decompress(tarball)).hexdigest()] * 2


@pytest.fixture
def small_limit(monkeypatch):
    monkeypatch.setattr("DashAI.back.plugins.sources.base.MAX_PLUGIN_BYTES", 1024)


def test_a_tarball_too_big_once_extracted_is_refused(small_limit):
    tarball = _make_tarball({"repo/data.bin": b"\0" * 4096})  # a tiny download

    _fails(_source_with_routes(_default_routes(tarball)), SourceError, "too big")


def test_a_release_file_too_big_is_refused_without_downloading_it(small_limit):
    calls = []
    asset = {**_asset("plugin.zip", ASSET_URL), "size": 4096}
    routes = _default_routes(assets=[asset], blobs={ASSET_URL: ZIP}, calls=calls)

    _fails(_source_with_routes(routes), SourceError, "too big")
    assert "/plugin.zip" not in calls


def _statement(sha256):
    return json.dumps(
        {
            "predicateType": "https://slsa.dev/provenance/v1",
            "subject": [{"name": "plugin.zip", "digest": {"sha256": sha256}}],
        }
    ).encode()


def _attested_source(verify, status_for=None, token=None, asset=True):
    """A release with one .zip asset and its attestations, recording requests."""
    base = _default_routes(
        _repo_tarball(),
        tag="v1.2.3",
        assets=[_asset("plugin.zip", ASSET_URL)] if asset else [],
        blobs={ASSET_URL: ZIP},
    )
    calls = []

    def routes(request):
        url = request.url
        calls.append((url.host, url.path, request.headers.get("authorization")))
        override = status_for(request) if status_for else None
        if override is not None:
            return override
        if "/attestations/" in url.path:
            return httpx.Response(200, json={"attestations": [{"bundle": {"b": 1}}]})
        return base(request)

    source = _source_with_routes(routes, verify_attestation=verify, token=lambda: token)
    return source, calls


def test_attested_when_the_signed_statement_covers_this_file():
    seen = {}

    def verify(bundle, repo_uri, ref):
        seen.update(bundle=bundle, repo_uri=repo_uri, ref=ref)
        return _statement(ZIP_SHA)

    source, calls = _attested_source(verify)
    with source.fetch(URL) as fetched:
        pass

    assert fetched.trust_level == "github_attested"
    assert [path for _, path, _ in calls if "/attestations/" in path] == [
        f"/repos/owner/repo/attestations/sha256:{ZIP_SHA}"
    ]
    assert seen == {
        "bundle": {"b": 1},
        "repo_uri": "https://github.com/owner/repo",
        "ref": "refs/tags/v1.2.3",
    }


def _signed_for_another_repo(*_):
    raise ValueError("Certificate's OIDCSourceRepositoryRef does not match")


@pytest.mark.parametrize(
    "verify", [lambda *_: _statement("0" * 64), _signed_for_another_repo]
)
def test_not_attested_when_the_statement_or_its_signature_does_not_match(verify):
    source, _ = _attested_source(verify)

    with source.fetch(URL) as fetched:
        assert (fetched.path / "manifest.json").is_file()  # install still proceeds

    assert fetched.trust_level == "github_asset"


RELEASE_URL = "https://github.com/owner/repo/releases/download/v1.2.3/plugin.zip"
BUNDLE_URL = "https://raw.example/bundles/repo/v1.2.3.json"


def _listed(source, url=RELEASE_URL, sha256=ZIP_SHA, bundle_url=BUNDLE_URL):
    return source.fetch_listed(
        URL,
        "v1.2.3",
        kind="asset",
        sha256=sha256,
        commit="c" * 40,
        url=url,
        size=len(ZIP),
        bundle_url=bundle_url,
    )


def _store_hosts(bundle=b'{"b": 1}'):
    """A source serving the release file and its bundle, recording hosts."""
    files = {RELEASE_URL: ZIP, BUNDLE_URL: bundle}
    hosts = []

    def routes(request):
        hosts.append(request.url.host)
        content = files[str(request.url)]
        if isinstance(content, int):
            return httpx.Response(content)
        return httpx.Response(200, content=content)

    source = _source_with_routes(
        routes, verify_attestation=lambda *_: _statement(ZIP_SHA)
    )
    return source, hosts


@pytest.mark.parametrize(
    ("bundle", "level"), [(b'{"b": 1}', "github_attested"), (404, "github_asset")]
)
def test_a_listed_release_is_fetched_without_the_api(bundle, level):
    source, hosts = _store_hosts(bundle)

    with _listed(source) as fetched:
        assert (fetched.path / "manifest.json").is_file()

    assert fetched.trust_level == level  # a missing bundle is not attested
    assert hosts == ["github.com", "raw.example"]


def test_an_unsigned_listed_release_is_only_a_file_of_that_release():
    source, _ = _store_hosts()

    unsigned = _listed(source, url=ASSET_URL, bundle_url=None)
    with pytest.raises(GitHubSourceError, match="Not a file"), unsigned:
        pass


def test_a_listed_release_with_other_bytes_is_refused():
    source, _ = _store_hosts()

    with pytest.raises(GitHubSourceError) as error, _listed(source, sha256="0" * 64):
        pass

    assert error.value.code == "digest_mismatch"


def test_token_goes_only_to_the_rest_api():
    source, calls = _attested_source(lambda *_: _statement(ZIP_SHA), token="ghp_s")

    with source.fetch(URL):
        pass

    api = [auth for host, _, auth in calls if host == "api.github.com"]
    downloads = [auth for host, _, auth in calls if host != "api.github.com"]
    assert api
    assert all(auth == "Bearer ghp_s" for auth in api)
    assert downloads
    assert all(auth is None for auth in downloads)


def test_rate_limited_attestation_is_not_retried(monkeypatch):
    import DashAI.back.plugins.sources.github_source as module

    slept = []
    monkeypatch.setattr(module.time, "sleep", slept.append)

    def status_for(request):
        if "/attestations/" in request.url.path:
            return httpx.Response(403, headers={"x-ratelimit-remaining": "0"})
        return None

    source, calls = _attested_source(lambda *_: b"", status_for)
    _fails(source, GitHubRateLimitError)

    assert len([path for _, path, _ in calls if "/attestations/" in path]) == 1
    assert slept == []
