"""HuggingFace Hub credential."""

import logging
from typing import Final

from DashAI.back.core.utils import MultilingualString
from DashAI.back.credentials.base_credential import BaseCredential

logger = logging.getLogger(__name__)


class HuggingFaceCredential(BaseCredential):
    """Credential for the HuggingFace Hub."""

    DISPLAY_NAME: Final = MultilingualString(en="HuggingFace")
    DESCRIPTION: Final = MultilingualString(
        en="Access token for the HuggingFace Hub. Required for gated models and "
        "datasets."
    )
    ICON: str = "Key"

    def verify(self, key: str) -> bool:
        """Validate a HuggingFace token via ``whoami``.

        Parameters
        ----------
        key : str
            HuggingFace access token.

        Returns
        -------
        bool
            True if the token is valid.
        """
        from huggingface_hub import HfApi

        try:
            HfApi().whoami(token=key)
            return True
        except Exception as exc:
            logger.info("HuggingFace credential verification failed: %s", exc)
            return False

    def apply(self) -> None:
        """Log in to the HuggingFace Hub if a key is stored."""
        key = self.get_key()
        if not key:
            return None
        from huggingface_hub import login

        login(token=key)
        return None
