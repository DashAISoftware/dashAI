import os

from pydantic_settings import BaseSettings

curr_path = os.path.dirname(os.path.realpath(__file__))
dashai_path = os.path.dirname(curr_path)


class DefaultSettings(BaseSettings):
    """Default settings for DashAI."""

    FRONT_BUILD_PATH: str = os.path.join(dashai_path, "front/build")
    API_V0_STR: str = "/api/v0"
    API_V1_STR: str = "/api/v1"

    LOCAL_PATH: str = "~/.DashAI"
    SQLITE_DB_PATH: str = "db.sqlite"
    DATASETS_PATH: str = "datasets"
    RUNS_PATH: str = "runs"
    EXPLANATIONS_PATH: str = "explanations"
    EXPLORATIONS_PATH: str = "explorations"
