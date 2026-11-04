"""OpenML credential."""

import logging
from contextlib import contextmanager
from typing import Final, Iterator

import httpx
from kink import di

from DashAI.back.core.utils import MultilingualString
from DashAI.back.credentials.base_credential import BaseCredential

logger = logging.getLogger(__name__)


class OpenMLCredential(BaseCredential):
    """Credential for the OpenML API.

    The key is an OpenML API key, found in the user's profile under
    "API key".  OpenML only requires it to publish, so the hub search and
    download keep working without it.

    The ``openml`` library keeps the server and API key in module-level
    globals, so this credential does not change them permanently.  Use
    :meth:`configured` to set them only for the duration of an upload.
    """

    DISPLAY_NAME: Final = MultilingualString(
        en="OpenML",
        es="OpenML",
        pt="OpenML",
        de="OpenML",
        zh="OpenML",
    )
    DESCRIPTION: Final = MultilingualString(
        en=(
            "OpenML API key, found in your OpenML profile under 'API key'. "
            "Required to publish datasets."
        ),
        es=(
            "API key de OpenML, disponible en tu perfil de OpenML en 'API key'. "
            "Necesaria para publicar datasets."
        ),
        pt=(
            "Chave de API do OpenML, disponível no seu perfil do OpenML em "
            "'API key'. Necessária para publicar conjuntos de dados."
        ),
        de=(
            "OpenML-API-Schlüssel, zu finden in Ihrem OpenML-Profil unter "
            "'API key'. Erforderlich zum Veröffentlichen von Datensätzen."
        ),
        zh=(
            "OpenML API 密钥，可在 OpenML 个人资料的 'API key' 中找到。"
            "发布数据集时需要。"
        ),
    )
    ICON: str = "Key"

    @staticmethod
    def _server() -> str:
        """Return the configured OpenML server URL."""
        return di["config"]["OPENML_SERVER"]

    def verify(self, key: str) -> bool:
        """Validate an OpenML API key against the configured server.

        OpenML answers any request carrying an invalid key with an
        authentication error, so a minimal listing call is enough.  The
        request is made directly so the ``openml`` globals are not touched.

        Parameters
        ----------
        key : str
            OpenML API key.

        Returns
        -------
        bool
            True if the server accepts the key.
        """
        if not key or not key.strip():
            return False
        try:
            response = httpx.get(
                f"{self._server()}/data/list/limit/1",
                params={"api_key": key},
                timeout=30,
            )
            return response.status_code == 200
        except Exception as exc:
            logger.info("OpenML credential verification failed: %s", exc)
            return False

    @contextmanager
    def configured(self) -> Iterator[None]:
        """Point the ``openml`` library at the configured server and key.

        The previous server and API key are restored on exit, even when the
        block raises, so other users of the library in the same process
        (such as the hub dataset search) keep their own settings.

        Yields
        ------
        None

        Raises
        ------
        ValueError
            If no OpenML API key is stored.
        """
        key = self.get_key()
        if not key:
            raise ValueError("No OpenML API key is stored.")

        import openml

        previous_server = openml.config.server
        previous_key = openml.config.apikey
        openml.config.server = self._server()
        openml.config.apikey = key
        try:
            yield
        finally:
            openml.config.server = previous_server
            openml.config.apikey = previous_key
