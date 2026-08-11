from typing import Literal

from pydantic import BaseModel


class InsightGenerationParams(BaseModel):
    """Request body to generate an AI insight for one explainer artifact.

    Parameters
    ----------
    artifact_title : str
        The title of the artifact/group to analyze, exactly as shown by the
        frontend's selector (e.g. ``"Feature: age - Class: yes"``).
    provider_kind : Literal["local", "remote"]
        Which ``InsightProvider`` family answers the request.
    provider_params : dict
        Provider-specific parameters (e.g. ``{"model_name": "..."}`` for a
        local model).
    language : str
        Language the generated insight should be written in.
    """

    artifact_title: str
    provider_kind: Literal["local", "remote"] = "local"
    provider_params: dict = {}
    language: str = "en"
