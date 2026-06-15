from unittest.mock import MagicMock, patch

from DashAI.back.credentials.github_credential import GithubCredential
from DashAI.back.credentials.huggingface_credential import HuggingFaceCredential
from DashAI.back.credentials.kaggle_credential import KaggleCredential


def test_huggingface_verify_success():
    cred = HuggingFaceCredential()
    with patch("huggingface_hub.HfApi") as hf_api:
        hf_api.return_value.whoami.return_value = {"name": "user"}
        assert cred.verify("hf_good") is True


def test_huggingface_verify_failure():
    cred = HuggingFaceCredential()
    with patch("huggingface_hub.HfApi") as hf_api:
        hf_api.return_value.whoami.side_effect = Exception("401")
        assert cred.verify("hf_bad") is False


def test_github_verify_success():
    cred = GithubCredential()
    with patch("requests.get") as get:
        get.return_value = MagicMock(status_code=200)
        assert cred.verify("ghp_good") is True


def test_github_verify_failure():
    cred = GithubCredential()
    with patch("requests.get") as get:
        get.return_value = MagicMock(status_code=401)
        assert cred.verify("ghp_bad") is False


def test_kaggle_verify_success():
    cred = KaggleCredential()
    with patch("kaggle.api.kaggle_api_extended.KaggleApi") as api:
        api.return_value.authenticate.return_value = None
        assert cred.verify("user:key") is True


def test_kaggle_verify_failure():
    cred = KaggleCredential()
    with patch("kaggle.api.kaggle_api_extended.KaggleApi") as api:
        api.return_value.authenticate.side_effect = Exception("bad")
        assert cred.verify("nope") is False
