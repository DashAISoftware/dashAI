"""Persistence boundary for encrypted credentials."""

import logging
from datetime import datetime
from typing import Dict, Union

from DashAI.back.credentials.encryptor import CredentialEncryptor
from DashAI.back.dependencies.database.models import Credential

logger = logging.getLogger(__name__)


class CredentialStore:
    """Reads and writes encrypted credentials in the database.

    This is the only component that touches the credential table and the
    encryptor. Every credential belongs to a user, so every method takes the
    id of the user whose credential is read or written.
    """

    def __init__(self, session_factory, encryptor: CredentialEncryptor) -> None:
        """Initialize the store.

        Parameters
        ----------
        session_factory
            SQLAlchemy session factory (callable returning a session).
        encryptor : CredentialEncryptor
            Encryptor used to protect keys at rest.
        """
        self._session_factory = session_factory
        self._encryptor = encryptor

    @staticmethod
    def _find(db, name: str, user_id: int) -> Union[Credential, None]:
        return db.query(Credential).filter_by(user_id=user_id, name=name).first()

    def save(self, name: str, key: str, *, user_id: int) -> None:
        """Encrypt and persist a user's credential key, marking it verified.

        Parameters
        ----------
        name : str
            Credential component name.
        key : str
            Plaintext key to store.
        user_id : int
            Owner of the credential.
        """
        encrypted = self._encryptor.encrypt(key)
        with self._session_factory() as db:
            row = self._find(db, name, user_id)
            if row is None:
                row = Credential(
                    user_id=user_id, name=name, encrypted_key=encrypted, verified=True
                )
                db.add(row)
            else:
                row.encrypted_key = encrypted
                row.verified = True
                row.last_modified = datetime.now()
            db.commit()

    def load(self, name: str, *, user_id: int) -> Union[str, None]:
        """Return a user's decrypted key for a credential, or None.

        Parameters
        ----------
        name : str
            Credential component name.
        user_id : int
            Owner of the credential.

        Returns
        -------
        Union[str, None]
            Decrypted key, or None if not stored.
        """
        with self._session_factory() as db:
            row = self._find(db, name, user_id)
            if row is None:
                return None
            return self._encryptor.decrypt(row.encrypted_key)

    def is_verified(self, name: str, *, user_id: int) -> bool:
        """Return whether a user has the credential stored and verified.

        Parameters
        ----------
        name : str
            Credential component name.
        user_id : int
            Owner of the credential.

        Returns
        -------
        bool
            True if a verified key exists.
        """
        with self._session_factory() as db:
            row = self._find(db, name, user_id)
            return bool(row and row.verified)

    def delete(self, name: str, *, user_id: int) -> None:
        """Remove a user's stored credential.

        Parameters
        ----------
        name : str
            Credential component name.
        user_id : int
            Owner of the credential.
        """
        with self._session_factory() as db:
            row = self._find(db, name, user_id)
            if row is not None:
                db.delete(row)
                db.commit()

    def all_statuses(self, *, user_id: int) -> Dict[str, bool]:
        """Return the verified status of every credential a user stored.

        Parameters
        ----------
        user_id : int
            Owner of the credentials.

        Returns
        -------
        Dict[str, bool]
            Mapping of credential name to verified status.
        """
        with self._session_factory() as db:
            rows = db.query(Credential).filter_by(user_id=user_id).all()
            return {row.name: bool(row.verified) for row in rows}
