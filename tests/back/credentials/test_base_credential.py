import pytest
from cryptography.fernet import Fernet
from kink import di
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.auth.acting_user import acting_as
from DashAI.back.credentials.base_credential import BaseCredential
from DashAI.back.credentials.encryptor import CredentialEncryptor
from DashAI.back.credentials.store import CredentialStore
from DashAI.back.dependencies.database.models import Base


class FakeCredential(BaseCredential):
    DISPLAY_NAME = "Fake"
    DESCRIPTION = "Fake credential for tests"
    last_seen_key = None

    def verify(self, key: str) -> bool:
        return key == "good"


@pytest.fixture(autouse=True)
def credential_store_in_di():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    encryptor = CredentialEncryptor(Fernet.generate_key())
    di["credential_store"] = CredentialStore(session_factory, encryptor)
    yield
    del di["credential_store"]


def test_auth_stores_valid_key():
    cred = FakeCredential()
    with acting_as(1):
        assert cred.auth("good") is True
        assert cred.get_key() == "good"
        assert cred.is_authenticated() is True


def test_auth_rejects_invalid_key():
    cred = FakeCredential()
    with acting_as(1):
        with pytest.raises(ValueError, match="Invalid credential"):
            cred.auth("bad")
        assert cred.get_key() is None
        assert cred.is_authenticated() is False


def test_keys_belong_to_the_acting_user():
    cred = FakeCredential()
    with acting_as(1):
        cred.auth("good")

    with acting_as(2):
        assert cred.get_key() is None
        assert cred.is_authenticated() is False


def test_acting_for_nobody_has_no_key_and_cannot_store_one():
    cred = FakeCredential()
    with acting_as(1):
        cred.auth("good")

    assert cred.get_key() is None
    assert cred.is_authenticated() is False
    with pytest.raises(RuntimeError):
        cred.auth("good")


def test_apply_is_noop_without_key():
    cred = FakeCredential()
    # should not raise even though nothing is stored
    cred.apply()


def test_type_is_credential():
    assert FakeCredential.TYPE == "Credential"
