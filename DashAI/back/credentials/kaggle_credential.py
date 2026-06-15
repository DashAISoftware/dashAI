"""Kaggle credential."""

import logging
from typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.credentials.base_credential import BaseCredential

logger = logging.getLogger(__name__)


class KaggleCredential(BaseCredential):
    """Credential for the Kaggle API.

    The key is expected in the form ``"username:api_key"``.
    """

    DISPLAY_NAME: Final = MultilingualString(en="Kaggle")
    DESCRIPTION: Final = MultilingualString(
        en="Kaggle API credential in the form 'username:key'."
    )
    ICON: str = "Key"

    def verify(self, key: str) -> bool:
        """Validate a Kaggle credential via the public API.

        The credential is checked with an authenticated request to the Kaggle
        REST API using HTTP basic auth, which avoids importing the ``kaggle``
        package (its import performs an eager, interactive authentication that
        can terminate the process when no local credentials exist).

        Parameters
        ----------
        key : str
            Kaggle credential in the form ``"username:api_key"``.

        Returns
        -------
        bool
            True if the credential authenticates successfully.
        """
        import requests

        try:
            username, separator, api_key = key.partition(":")
            if not separator or not username or not api_key:
                return False
            response = requests.get(
                "https://www.kaggle.com/api/v1/datasets/list",
                auth=(username, api_key),
                timeout=10,
            )
            return response.status_code == 200
        except Exception as exc:
            logger.info("Kaggle credential verification failed: %s", exc)
            return False
