"""Tests for OpenMLCredential."""

from unittest.mock import MagicMock, patch

import openml
import pytest

from DashAI.back.config import DefaultSettings
from DashAI.back.credentials.openml_credential import OpenMLCredential

TEST_SERVER = "https://test.openml.org/api/v1/xml"


@pytest.fixture
def cred():
    with patch.object(OpenMLCredential, "_server", return_value=TEST_SERVER):
        yield OpenMLCredential()


def test_default_server_is_test_server():
    assert DefaultSettings().OPENML_SERVER == TEST_SERVER


def test_verify_empty_key(cred):
    assert cred.verify("") is False
    assert cred.verify("   ") is False


def test_verify_success(cred):
    with patch("httpx.get") as get:
        get.return_value = MagicMock(status_code=200)
        assert cred.verify("good_key") is True
    get.assert_called_once_with(
        f"{TEST_SERVER}/data/list/limit/1",
        params={"api_key": "good_key"},
        timeout=30,
    )


def test_verify_rejected_key(cred):
    with patch("httpx.get") as get:
        get.return_value = MagicMock(status_code=412)
        assert cred.verify("bad_key") is False


def test_verify_network_error(cred):
    with patch("httpx.get", side_effect=Exception("offline")):
        assert cred.verify("good_key") is False


def test_configured_sets_and_restores_openml_globals(cred):
    previous = (openml.config.server, openml.config.apikey)
    with (
        patch.object(cred, "get_key", return_value="stored_key"),
        cred.configured(),
    ):
        assert openml.config.server == TEST_SERVER
        assert openml.config.apikey == "stored_key"
    assert (openml.config.server, openml.config.apikey) == previous


def test_configured_restores_globals_on_error(cred):
    previous = (openml.config.server, openml.config.apikey)
    with (
        patch.object(cred, "get_key", return_value="stored_key"),
        pytest.raises(RuntimeError, match="upload failed"),
        cred.configured(),
    ):
        raise RuntimeError("upload failed")
    assert (openml.config.server, openml.config.apikey) == previous


def test_configured_requires_stored_key(cred):
    with (
        patch.object(cred, "get_key", return_value=None),
        pytest.raises(ValueError, match="No OpenML API key"),
        cred.configured(),
    ):
        pass
