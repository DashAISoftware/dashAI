import pytest
from cryptography.fernet import Fernet
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from DashAI.back.credentials.encryptor import CredentialEncryptor
from DashAI.back.credentials.store import CredentialStore
from DashAI.back.dependencies.database.models import Base


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


@pytest.fixture
def store(session_factory):
    encryptor = CredentialEncryptor(Fernet.generate_key())
    return CredentialStore(session_factory, encryptor)


USER = 1
OTHER_USER = 2


def test_save_and_load_roundtrip(store):
    store.save("HuggingFaceCredential", "hf_token_123", user_id=USER)
    assert store.load("HuggingFaceCredential", user_id=USER) == "hf_token_123"


def test_save_marks_verified(store):
    store.save("HuggingFaceCredential", "hf_token_123", user_id=USER)
    assert store.is_verified("HuggingFaceCredential", user_id=USER) is True


def test_load_missing_returns_none(store):
    assert store.load("Missing", user_id=USER) is None
    assert store.is_verified("Missing", user_id=USER) is False


def test_save_is_upsert(store):
    store.save("HuggingFaceCredential", "old", user_id=USER)
    store.save("HuggingFaceCredential", "new", user_id=USER)
    assert store.load("HuggingFaceCredential", user_id=USER) == "new"


def test_delete_removes_key(store):
    store.save("HuggingFaceCredential", "tok", user_id=USER)
    store.delete("HuggingFaceCredential", user_id=USER)
    assert store.load("HuggingFaceCredential", user_id=USER) is None
    assert store.is_verified("HuggingFaceCredential", user_id=USER) is False


def test_all_statuses(store):
    store.save("HuggingFaceCredential", "tok", user_id=USER)
    store.save("GithubCredential", "ghp", user_id=USER)
    assert store.all_statuses(user_id=USER) == {
        "HuggingFaceCredential": True,
        "GithubCredential": True,
    }


def test_credentials_are_kept_per_user(store):
    store.save("HuggingFaceCredential", "tok_user", user_id=USER)

    assert store.load("HuggingFaceCredential", user_id=OTHER_USER) is None
    assert store.is_verified("HuggingFaceCredential", user_id=OTHER_USER) is False
    assert store.all_statuses(user_id=OTHER_USER) == {}

    store.save("HuggingFaceCredential", "tok_other", user_id=OTHER_USER)
    store.delete("HuggingFaceCredential", user_id=USER)
    assert store.load("HuggingFaceCredential", user_id=OTHER_USER) == "tok_other"
