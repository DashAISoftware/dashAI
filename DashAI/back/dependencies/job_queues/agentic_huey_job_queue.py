import logging
import os
import warnings
from pathlib import Path

from DashAI.back.dependencies.job_queues.huey_job_queue import HueyJobQueue

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

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


_lp_str = os.environ.get("DASHAI_LOCAL_PATH")
_lp = Path(os.path.expanduser(_lp_str)) if _lp_str else Path.home() / ".DashAI"
_lp.mkdir(parents=True, exist_ok=True)
_job_queue = HueyJobQueue("agent_job_queue", path_db=str(_lp))
agent_huey = _job_queue.huey


@agent_huey.on_startup()
def create_container_huey():
    from DashAI.back.container import build_container
    from DashAI.back.dependencies.config_builder import build_config_dict

    local_path = _lp
    logging_level = os.environ.get("DASHAI_LOGGING_LEVEL", "INFO")

    config = build_config_dict(local_path=local_path, logging_level=logging_level)
    build_container(config)
