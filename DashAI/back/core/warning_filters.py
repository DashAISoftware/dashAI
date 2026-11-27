"""Warnings that third-party packages print at import time and users cannot act on."""

import warnings


def silence_startup_warnings() -> None:
    """Hide the noisy startup warnings in the app and in the Huey processes."""
    warnings.filterwarnings(
        "ignore",
        message=".*mediapipe.*",
        category=UserWarning,
        module="controlnet_aux",
    )
    warnings.filterwarnings(
        "ignore",
        message=".*Importing from timm.models.layers.*",
        category=FutureWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*Importing from timm.models.registry.*",
        category=FutureWarning,
    )
    warnings.filterwarnings(
        "ignore",
        message=".*Overwriting tiny_vit.*",
        category=UserWarning,
        module="controlnet_aux",
    )
    warnings.filterwarnings(
        "ignore",
        message=".*found in sys.modules after import.*",
        category=RuntimeWarning,
    )
