import logging
from typing import TYPE_CHECKING, Any, Dict, Type

from kink import inject

from DashAI.back.config import DefaultSettings
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from DashAI.back.dependencies.registry.component_registry import ComponentRegistry

log = logging.getLogger(__name__)


class DataExploration(BaseJob):
    """
    DataExploration node for performing data exploration in pipelines.

    It supports multiple exploration types and saves results to files.

    Parameters
    ----------
    explorations : Dict[str, Any]
        - exploration_type: Type of exploration to perform
        - parameters: Parameters for the exploration
        - columns: Columns to explore
        - id: Unique identifier for the exploration
        - name: Name of the exploration
    """

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
        log.debug("DataExploration executed successfully.")

    def set_status_as_error(self) -> None:
        log.error("DataExploration encountered an error.")

    def get_job_name(self) -> str:
        return "DataExploration"

    @inject
    async def run(
        self,
        context: Dict[str, Any],
        component_registry: "ComponentRegistry" = lambda di: di["component_registry"],
    ) -> Dict[str, Any]:
        try:
            import inspect
            import os
            from pathlib import Path

            pipeline_id = context.get("pipeline_id")
            node_id = context.get("_node_id", "DataExploration")
            loaded_dataset = context.get("dataset")

            settings = DefaultSettings()
            sqlite_local = os.path.expanduser(settings.LOCAL_PATH)
            base_path = (
                Path(sqlite_local)
                / "pipelines"
                / "exploration"
                / str(pipeline_id)
                / str(node_id)
            )
            base_path.mkdir(parents=True, exist_ok=True)

            results = {}

            for idx, option in enumerate(self.explorations):
                try:
                    exploration_type = option["exploration_type"]
                    parameters = option.get("parameters", {})
                    columns = option.get("columns", [])
                    explorer_id = option.get("id", str(idx))
                    name = option.get("name", "")

                    explorer_component_class: Type[BaseExplorer] = component_registry[
                        exploration_type
                    ]["class"]
                    explorer_instance = explorer_component_class(**parameters)
                    assert isinstance(explorer_instance, BaseExplorer)

                    prepared_dataset = explorer_instance.prepare_dataset(
                        loaded_dataset, columns
                    )

                    # Create a simple explorer info object for pipeline execution
                    # This is not a database object,
                    # just a container for explorer metadata
                    class ExplorerInfo:
                        def __init__(
                            self, exploration_type, columns, parameters, id, name
                        ):
                            self.exploration_type = exploration_type
                            self.columns = columns
                            self.parameters = parameters
                            self.id = id
                            self.name = name

                    explorer_info = ExplorerInfo(
                        exploration_type=exploration_type,
                        columns=columns,
                        parameters=parameters,
                        id=explorer_id,
                        name=name,
                    )

                    result = explorer_instance.launch_exploration(
                        prepared_dataset, explorer_info
                    )

                    save_notebook_sig = inspect.signature(
                        explorer_instance.save_notebook
                    )
                    save_notebook_params = set(save_notebook_sig.parameters)

                    notebook_info_arg_name = None
                    for candidate in (
                        "__notebook_info__",
                        "__exploration_info__",
                        "notebook_info",
                    ):
                        if candidate in save_notebook_params:
                            notebook_info_arg_name = candidate
                            break

                    save_notebook_kwargs = {
                        "explorer_info": explorer_info,
                        "save_path": base_path,
                        "result": result,
                    }
                    if notebook_info_arg_name is not None:
                        save_notebook_kwargs[notebook_info_arg_name] = None
                        save_path = explorer_instance.save_notebook(
                            **save_notebook_kwargs
                        )
                    else:
                        # Fallback to positional first arg for legacy implementations.
                        save_path = explorer_instance.save_notebook(
                            None,
                            explorer_info=explorer_info,
                            save_path=base_path,
                            result=result,
                        )

                    results[str(explorer_id)] = {
                        "exploration_type": exploration_type,
                        "path": str(save_path),
                        "parameters": parameters,
                        "name": name,
                    }

                except Exception as e:
                    log.exception(e)
                    raise JobError(
                        f"Failed to execute data exploration: {exploration_type}"
                    ) from e

            return {"exploration": results}

        except Exception as e:
            log.exception(e)
            raise JobError("Error while running DataExploration job.") from e
