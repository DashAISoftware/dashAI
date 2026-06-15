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
        """Validate a Kaggle credential by authenticating.

        Parameters
        ----------
        key : str
            Kaggle credential in the form ``"username:api_key"``.

        Returns
        -------
        bool
            True if authentication succeeds.
        """
        import os

        from kaggle.api.kaggle_api_extended import KaggleApi

        try:
            username, _, api_key = key.partition(":")
            os.environ["KAGGLE_USERNAME"] = username
            os.environ["KAGGLE_KEY"] = api_key
            KaggleApi().authenticate()
            return True
        except Exception as exc:
            logger.info("Kaggle credential verification failed: %s", exc)
            return False
