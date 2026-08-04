import logging
import pickle
from typing import TYPE_CHECKING, Any, Dict

from kink import inject
from sqlalchemy import exc

from DashAI.back.core.artifacts import Artifact, GroupedArtifacts
from DashAI.back.dependencies.database.models import (
    GlobalExplainer,
    LocalExplainer,
    Run,
)
from DashAI.back.job.base_job import BaseJob, JobError

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)


class ExplainerStoryJob(BaseJob):
    """Generate a natural-language story for an already-computed explanation.

    Unlike ``ExplainerJob``, this job never recomputes an explanation: it
    reloads the explanation and plot artifacts already persisted on disk and
    reinstantiates the explainer purely to call its ``story`` method, which
    is the pattern that method's docstring is written around (see
    ``BaseGlobalExplainer.story`` / ``BaseLocalExplainer.story``).
    """

    @inject
    def set_status_as_delivered(self) -> None:
        log.debug("Explainer story job marked as delivered")

    @inject
    def set_status_as_error(self) -> None:
        log.debug("Explainer story job failed")

    @inject
    def get_job_name(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> str:
        """Get a descriptive name for the job."""
        explainer_id = self.kwargs.get("explainer_id")
        explainer_scope = self.kwargs.get("explainer_scope", "")

        if not explainer_id:
            return f"{explainer_scope.capitalize()} Story"

        try:
            with session_factory() as db:
                model_cls = (
                    GlobalExplainer if explainer_scope == "global" else LocalExplainer
                )
                explainer = db.get(model_cls, explainer_id)
                if explainer and explainer.name:
                    return f"Story: {explainer.name}"
                if explainer and explainer.explainer_name:
                    return f"Story: {explainer.explainer_name.split('.')[-1]}"
        except Exception as e:
            log.exception(f"Error getting job name: {e}")

        return f"{explainer_scope.capitalize()} Story ({explainer_id})"

    def _load_explainer(self, db: "Session", explainer_db, component_registry):
        """Reinstantiate the explainer that produced an already-computed explanation.

        Skips ``fit`` and ``explain``/``explain_instance`` (the expensive
        steps): the explanation is reloaded from its pickle instead of
        recomputed.
        """
        run: Run = db.get(Run, explainer_db.run_id)
        if not run:
            raise JobError(f"Run {explainer_db.run_id} does not exist in DB.")

        try:
            model_class = component_registry[run.model_name]["class"]
            model = model_class(**run.parameters)
            trained_model = model.load(run.run_path)
        except Exception as e:
            log.exception(e)
            raise JobError(f"Unable to load model for run {run.id}") from e

        try:
            explainer_class = component_registry[explainer_db.explainer_name]["class"]
            explainer = explainer_class(model=trained_model, **explainer_db.parameters)
        except Exception as e:
            log.exception(e)
            raise JobError(
                f"Unable to instantiate explainer {explainer_db.explainer_name}"
            ) from e

        try:
            with open(explainer_db.explanation_path, "rb") as file:
                explainer.explanation = pickle.load(file)
        except Exception as e:
            log.exception(e)
            raise JobError("Unable to load the saved explanation") from e

        return explainer

    @staticmethod
    def _parse_artifact(item: Dict[str, Any]):
        """Reconstruct an ``Artifact``/``GroupedArtifacts`` from its saved wire dict."""
        if item.get("type") == "grouped":
            return GroupedArtifacts.model_validate(item)
        return Artifact.from_dict(item)

    def _generate_global_story(
        self, db: "Session", explainer_db, component_registry
    ) -> str:
        explainer = self._load_explainer(db, explainer_db, component_registry)

        artifact_index = self.kwargs.get("artifact_index", 0)
        try:
            with open(explainer_db.plot_path, "rb") as file:
                plots = pickle.load(file)
            explainer_output = self._parse_artifact(plots[artifact_index])
        except Exception as e:
            log.exception(e)
            raise JobError("Unable to load the saved plot artifacts") from e

        try:
            return explainer.story(explainer_output)
        except NotImplementedError as e:
            raise JobError(str(e)) from e
        except Exception as e:
            log.exception(e)
            raise JobError("Failed to generate the story") from e

    def _generate_local_story(
        self, db: "Session", explainer_db, component_registry
    ) -> str:
        from DashAI.back.dataloaders.classes.dashai_dataset import load_dataset

        group_index = self.kwargs.get("group_index")
        if group_index is None:
            raise JobError("group_index is required to generate a local story")

        explainer = self._load_explainer(db, explainer_db, component_registry)

        artifact_index = self.kwargs.get("artifact_index", 0)
        try:
            with open(explainer_db.plots_path, "rb") as file:
                plots = pickle.load(file)
            full_grouped = GroupedArtifacts.model_validate(plots[artifact_index])
            group = full_grouped.groups[group_index]
            explainer_output = GroupedArtifacts(groups=[group])
        except IndexError as e:
            raise JobError(f"No explained instance at index {group_index}") from e
        except Exception as e:
            log.exception(e)
            raise JobError("Unable to load the saved plot artifacts") from e

        try:
            prediction_context = load_dataset(
                f"{explainer_db.input_dataset_path}/dataset"
            ).select([group_index])
        except Exception as e:
            log.exception(e)
            raise JobError("Unable to load the explained instance") from e

        try:
            return explainer.story(explainer_output, prediction_context)
        except NotImplementedError as e:
            raise JobError(str(e)) from e
        except Exception as e:
            log.exception(e)
            raise JobError("Failed to generate the story") from e

    @inject
    def run(self) -> None:
        from kink import di

        session_factory = di["session_factory"]
        component_registry = di["component_registry"]

        explainer_id: int = self.kwargs["explainer_id"]
        explainer_scope: str = self.kwargs["explainer_scope"]

        with session_factory() as db:
            if explainer_scope == "global":
                explainer_db: GlobalExplainer = db.get(GlobalExplainer, explainer_id)
            elif explainer_scope == "local":
                explainer_db: LocalExplainer = db.get(LocalExplainer, explainer_id)
            else:
                raise JobError(f"{explainer_scope} is an invalid explainer type")

            if not explainer_db:
                raise JobError(
                    f"Explainer with id {explainer_id} does not exist in DB."
                )
            if not explainer_db.explanation_path:
                raise JobError(
                    "The explanation has not been computed yet for this explainer."
                )

            try:
                if explainer_scope == "global":
                    story = self._generate_global_story(
                        db, explainer_db, component_registry
                    )
                    explainer_db.story = story
                else:
                    story = self._generate_local_story(
                        db, explainer_db, component_registry
                    )
                    explainer_db.stories = {
                        **(explainer_db.stories or {}),
                        str(self.kwargs.get("group_index")): story,
                    }
                db.commit()
            except JobError:
                db.rollback()
                raise
            except exc.SQLAlchemyError as e:
                log.exception(e)
                db.rollback()
                raise JobError("Error saving the generated story") from e
