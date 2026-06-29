import logging
from typing import TYPE_CHECKING, Type

from kink import inject
from sqlalchemy import exc

from DashAI.back.converters.converter_report import load_converter_report
from DashAI.back.core.enums.status import ConverterStatus
from DashAI.back.dependencies.database.models import Converter, Explorer, Notebook
from DashAI.back.exploration.base_explorer import BaseExplorer
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


def _build_explorer_context(
    db,
    notebook_info: Notebook,
    explorer_instance: BaseExplorer,
    config: dict,
) -> dict:
    """Build optional runtime context for explorers.

    Explorers keep receiving the current notebook dataset as their main input.
    A converter report is loaded only when the explorer explicitly requires it
    via ``metadata["requires_converter_report"] = True``.

    When the explorer also declares ``metadata["requires_converter_class"]``,
    only converters of that specific class are considered. Otherwise the most
    recently finished converter of any type is used.
    """
    explorer_metadata = explorer_instance.get_metadata()
    if not explorer_metadata.get("requires_converter_report", False):
        return {}

    required_class = explorer_metadata.get("requires_converter_class")
    converter_query = (
        db.query(Converter)
        .filter(Converter.notebook_id == notebook_info.id)
        .filter(Converter.status == ConverterStatus.FINISHED)
    )
    if required_class:
        converter_query = converter_query.filter(Converter.converter == required_class)
    latest_converter = converter_query.order_by(Converter.created.desc()).first()

    if latest_converter is None:
        class_hint = f" of type '{required_class}'" if required_class else ""
        raise JobError(
            f"This explorer requires a converter report, but the notebook has "
            f"no finished converters{class_hint}."
        )

    notebook_output_path = config["NOTEBOOK_PATH"] / str(notebook_info.id)
    converter_report = load_converter_report(
        notebook_output_path,
        latest_converter.id,
    )

    if converter_report is None:
        class_hint = f" '{required_class}'" if required_class else ""
        raise JobError(
            f"This explorer requires a converter report, but the latest "
            f"finished{class_hint} converter did not produce one."
        )

    required_algorithm = explorer_metadata.get("requires_algorithm")
    if required_algorithm:
        used_algorithm = converter_report.get("algorithm_key", "").lower()
        if used_algorithm != required_algorithm.lower():
            raise JobError(
                f"This explorer requires the '{required_algorithm}' clustering "
                f"algorithm, but the last Clustering converter ran '{used_algorithm}'"
                f". Re-run the Clustering converter selecting the "
                f"'{required_algorithm}' algorithm."
            )

    return {
        "converter_report": converter_report,
        "converter_report_source": {
            "converter_id": latest_converter.id,
            "converter": latest_converter.converter,
        },
    }


class ExplorerJob(BaseJob):
    """ExplorerJob class to launch explorations."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
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
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the explorer as error."""
        explorer_id: int = self.kwargs.get("explorer_id")
        if explorer_id is None:
            return

        with session_factory() as db:
            try:
                explorer: Explorer = db.query(Explorer).get(explorer_id)
                if explorer:
                    explorer.set_status_as_error()
                    db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job."""
        explorer_id = self.kwargs.get("explorer_id")
        if not explorer_id:
            return "Exploration"

        from kink import di

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                explorer: Explorer = db.query(Explorer).get(explorer_id)
                if explorer and explorer.name:
                    return f"Explore: {explorer.name}"
                if explorer and explorer.exploration_type:
                    return f"Explore: {explorer.exploration_type}"
        except Exception:
            pass

        return f"Exploration ({explorer_id})"

    @inject
    def run(
        self,
    ) -> None:
        import os
        import pathlib

        from kink import di

        from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

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

            try:
                explorer_context = _build_explorer_context(
                    db,
                    notebook_info,
                    explorer_instance,
                    config,
                )
                explorer_instance.set_context(explorer_context)
            except JobError:
                explorer_info.set_status_as_error()
                db.commit()
                raise
            except Exception as e:
                log.exception(e)
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(
                    "Error loading context for explorer "
                    f"{explorer_info.exploration_type}."
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
            except (JobError, ValueError) as e:
                explorer_info.set_status_as_error()
                db.commit()
                raise JobError(str(e)) from e
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
