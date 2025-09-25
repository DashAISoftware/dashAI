import logging
import os
import pathlib

from beartype.typing import Type
from kink import inject
from sqlalchemy import exc
from sqlalchemy.orm import sessionmaker

from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset
from DashAI.back.dependencies.database.models import (
    Explorer,
    GlobalExplainer,
    LocalExplainer,
    Notebook,
)
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.job.base_job import BaseJob, JobError

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ExplorerJob(BaseJob):
    """ExplorerJob class to launch explorations."""

    @inject
    def set_status_as_delivered(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the explorer as delivered."""
        explorer_id: int = self.kwargs["explorer_id"]

        with session_factory() as db:
            explorer: Explorer = db.query(Explorer).get(explorer_id)

            if explorer is None:
                raise JobError(f"Explorer with id {explorer_id} not found.")

            try:
                explorer.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError(
                    "Error while setting the status of the explorer as delivered."
                ) from e

    @inject
    def set_status_as_error(
        self, session_factory: sessionmaker = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the explainer as error."""
        explainer_id: int = self.kwargs.get("explainer_id")
        explainer_scope: str = self.kwargs.get("explainer_scope", "")

        if explainer_id is None:
            return

        with session_factory() as db:
            try:
                if explainer_scope == "global":
                    explainer = db.get(GlobalExplainer, explainer_id)
                elif explainer_scope == "local":
                    explainer = db.get(LocalExplainer, explainer_id)
                else:
                    return

                if explainer:
                    explainer.set_status_as_error()
                    db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        explainer_id = self.kwargs.get("explainer_id")
        explainer_scope = self.kwargs.get("explainer_scope", "")

        if not explainer_id:
            return f"{explainer_scope.capitalize()} Explanation"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                if explainer_scope == "global":
                    explainer = db.get(GlobalExplainer, explainer_id)
                elif explainer_scope == "local":
                    explainer = db.get(LocalExplainer, explainer_id)
                else:
                    return (
                        f"{explainer_scope.capitalize()} Explanation ({explainer_id})"
                    )

                if explainer and explainer.name:
                    return f"Explain: {explainer.name}"
                if explainer and explainer.explainer_name:
                    return f"Explain: {explainer.explainer_name.split('.')[-1]}"
        except Exception:
            pass

        return f"{explainer_scope.capitalize()} Explanation ({explainer_id})"

    @inject
    def run(
        self,
    ) -> None:
        from kink import di

        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]
        explorer_id: int = self.kwargs["explorer_id"]
        with session_factory() as db:
            # Load the explorer information
            try:
                explorer_info: Explorer = db.query(Explorer).get(explorer_id)
                if explorer_info is None:
                    raise JobError(f"Explorer with id {explorer_id} not found.")
                explorer_info.set_status_as_started()
                explorer_info.huey_id = self.kwargs.get("huey_id", None)
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Error while loading the explorer info.") from e

            # Load the notebook information
            try:
                notebook_info: Notebook = db.query(Notebook).get(
                    explorer_info.notebook_id
                )
                if notebook_info is None:
                    raise JobError(
                        f"Notebook with id {explorer_info.notebook_id} not found."
                    )
            except exc.SQLAlchemyError as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError("Error while loading the notebook info.") from e

            # Load the dataset from the notebook
            try:
                loaded_dataset = load_dataset(f"{notebook_info.file_path}/dataset")
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    f"Can not load dataset from path {notebook_info.file_path}",
                ) from e

            # obtain the explorer component from the registry
            try:
                explorer_component_class: Type[BaseExplorer] = component_registry[
                    explorer_info.exploration_type
                ]["class"]
            except KeyError as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    (
                        f"Explorer {explorer_info.exploration_type} "
                        "not found in the registry."
                    )
                ) from e

            # Instance the explorer (the explorer handles its validation)
            try:
                explorer_instance = explorer_component_class(**explorer_info.parameters)
                assert isinstance(explorer_instance, BaseExplorer)
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    f"Error instancing the explorer {explorer_info.exploration_type}."
                ) from e

            # prepare the dataset
            try:
                prepared_dataset = explorer_instance.prepare_dataset(
                    loaded_dataset, explorer_info.columns
                )
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    (
                        "Error preparing the dataset for the exploration "
                        f"{explorer_info.exploration_type}."
                    )
                ) from e

            # Launch the exploration
            try:
                result = explorer_instance.launch_exploration(
                    prepared_dataset, explorer_info
                )
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    f"Error launching the exploration {explorer_info.exploration_type}."
                ) from e

            # Save the result
            try:
                # save in the notebook folder
                save_path = pathlib.Path(
                    os.path.join(
                        config["NOTEBOOK_PATH"],
                        (f"{notebook_info.id}"),
                    )
                )
                if not save_path.exists():
                    save_path.mkdir(parents=True)

                save_path = explorer_instance.save_notebook(
                    notebook_info, explorer_info, save_path, result
                )
                if isinstance(save_path, str):
                    save_path = pathlib.Path(save_path)
                if not isinstance(save_path, pathlib.Path):
                    raise JobError(
                        (
                            f"Error while saving the exploration"
                            f" {explorer_info.exploration_type}"
                            f", save path is not a pathlib.Path."
                        )
                    )

                # Update the explorer info
                explorer_info.exploration_path = save_path.as_posix()
                explorer_info.set_status_as_finished()
                db.commit()
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    (
                        f"Error while saving the exploration "
                        f"{explorer_info.exploration_type}."
                    )
                ) from e
