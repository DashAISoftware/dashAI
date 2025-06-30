import logging
import os
import pathlib
from typing import Any, Dict, List, Type

from kink import di
import pandas as pd
from sqlalchemy import false
from DashAI.back.config import DefaultSettings
from DashAI.back.dependencies.database.models import Exploration, Explorer
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.job.base_job import BaseJob, JobError

log = logging.getLogger(__name__)

class DataExploration(BaseJob): 
    def __init__(
        self, 
        explorations: Dict[str, Any],
    ) -> None:
        super().__init__(
            kwargs={
                "explorations": explorations,
            }
        )
        self.explorations = explorations

    def set_status_as_delivered(self) -> None:
        log.info("DataExploration executed successfully.")

    def run(
        self, 
        context: Dict[str, Any],
        component_registry: ComponentRegistry = lambda di: di["component_registry"],
    ) -> Any:
        
        try:
            pipeline_id = context.get("pipeline_id")
            loaded_dataset = context.get("dataset")

            settings = DefaultSettings()
            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            base_path = pathlib.Path(sqlite_local) / "pipelines" / "exploration" / str(pipeline_id)
            base_path.mkdir(parents=True, exist_ok=True)

            results = {}

            for idx, option in enumerate(self.explorations):
                try:
                    exploration_type = option["exploration_type"]
                    parameters = option.get("parameters", {})
                    columns = option.get("columns", [])
                    id = option.get("id", str(idx))
                    name = option.get("name")

                    explorer_component_class: Type[BaseExplorer] = component_registry(di)[exploration_type]["class"]
                    explorer_instance = explorer_component_class(**parameters)
                    assert isinstance(explorer_instance, BaseExplorer)

                    prepared_dataset = explorer_instance.prepare_dataset(
                        loaded_dataset, columns
                    )

                    explorer_info = Explorer(
                        exploration_type=exploration_type,
                        columns=columns,
                        parameters=parameters,
                        id=id,
                    )
                        
                    result = explorer_instance.launch_exploration(
                        prepared_dataset, explorer_info
                    )
                        
                    save_path = explorer_instance.save_exploration(
                        __exploration_info__=None,
                        explorer_info=explorer_info,
                        save_path=base_path,
                        result=result,
                    )

                    results[str(id)] = {
                        "exploration_type": exploration_type,
                        "path": str(save_path),
                        "parameters": parameters,
                        "name": name,
                    }

                except Exception as e:
                    log.exception(e)
                    raise JobError(f"Failed to execute data exploration: {exploration_type}") from e

            return {"exploration": results}
        
        except Exception as e:
            log.exception(e)
            raise JobError("Error while running DataExploration job.") from e