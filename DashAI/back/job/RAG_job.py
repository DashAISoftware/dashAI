import gc
import logging
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict

from kink import di, inject
from sqlalchemy import exc
from sqlalchemy.orm import Session

from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
)
from DashAI.back.job.base_job import BaseJob, JobError, _release_frames
from DashAI.back.job.generative_failure import fail_process
from DashAI.back.models.RAG.RAG_constants import (
    RAG_OPTIONAL_MODEL_KEYS,
    RAG_OUTPUT_MESSAGE_TYPE,
    RAG_PARAM_KEYS,
    RAG_WORKFLOW_NAME,
)
from DashAI.back.models.RAG.RAG_pipeline import (
    RAGPipeline,
    RAGPipelineConfig,
)
from DashAI.back.services.RAG.cleanup_service import (
    IndexFootprint,
    capture_index_footprint,
    has_stale_index_rows,
    run_post_index_cleanup,
)
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.session_params import filter_pipeline_params
from DashAI.back.services.RAG.setup_service import SetupService

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.registry.component_registry import (
        ComponentRegistry,
    )
    from DashAI.back.tasks.base_generative_task import BaseGenerativeTask
    from DashAI.back.workflows.base_generative_workflow import (
        BaseGenerativeWorkflow,
    )

#: Session parameters the pipeline understands: the required model keys plus
#: the optional (but still pipeline-shaped) model keys such as the query
#: transformation stage. Any other key is filtered before the config guard.
_RAG_PARAM_KEYS = frozenset(RAG_PARAM_KEYS) | frozenset(RAG_OPTIONAL_MODEL_KEYS)

log = logging.getLogger(__name__)

#: Upper bound on the raw exception text surfaced in a user-visible job error.
#: Cause messages can be multi-KB and may embed absolute paths, SQL or URLs, so
#: they are truncated at the job boundary before being stored or displayed.
_JOB_ERROR_DETAIL_MAX_CHARS = 2000


def _empty_accelerator_cache() -> None:
    """Return cached CUDA blocks to the driver when torch is available.

    Kept best-effort: a missing torch installation or a failed cache clear
    must never replace the failure that ended the job.
    """
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        log.warning(
            "Could not clear the CUDA cache after RAG job cleanup.",
            exc_info=True,
        )


def _job_error(prefix: str, error: Exception) -> JobError:
    """Build a job error that preserves the underlying cause.

    Parameters
    ----------
    prefix : str
        Human-readable stage description, e.g. ``"Error during RAG pipeline
        setup"``.
    error : Exception
        The exception whose message is appended as the detail.

    Returns
    -------
    JobError
        A ``JobError`` formatted as ``"{prefix}: {detail}"``. The detail is the
        stripped exception message, truncated to
        ``_JOB_ERROR_DETAIL_MAX_CHARS`` with a trailing ellipsis when longer.
        When the detail is empty the bare ``prefix`` is returned.
    """
    detail = str(error).strip()
    if not detail:
        return JobError(prefix)
    if len(detail) > _JOB_ERROR_DETAIL_MAX_CHARS:
        detail = f"{detail[:_JOB_ERROR_DETAIL_MAX_CHARS]}…"
    return JobError(f"{prefix}: {detail}")


def _make_progress_reporter(
    session_factory: "sessionmaker", process_id: int
) -> Callable[[Dict[str, Any]], None]:
    """Build a best-effort live-progress reporter for a generative process.

    The pipeline calls the returned closure once per stage while the run is in
    flight. Each call opens a short-lived session, stores the payload on the
    process's ``progress`` column, and commits — so the chat frontend polling
    the process sees the current stage. A write is ignored unless the process is
    still ``STARTED``, so a late event cannot revive progress on a terminal
    (finished/error/cancelled) process.

    Reporting is best-effort: any failure is logged as a warning and swallowed.
    A transient DB error must never fail the chat turn, so the guard lives here
    rather than in the pipeline (which deliberately does not catch reporter
    exceptions).

    Parameters
    ----------
    session_factory : sessionmaker
        SQLAlchemy session factory.
    process_id : int
        The generative process whose ``progress`` column is updated.

    Returns
    -------
    Callable[[Dict[str, Any]], None]
        A reporter accepting one stage payload.

    """

    def report(progress: Dict[str, Any]) -> None:
        """Persist one stage payload, swallowing any failure."""
        try:
            with session_factory() as db:
                process: GenerativeProcess = db.get(GenerativeProcess, process_id)
                if process is None or process.status != RunStatus.STARTED:
                    return
                process.set_progress(progress)
                db.commit()
        except Exception as e:
            log.warning("Failed to report progress for process %s: %s", process_id, e)

    return report


def _load_turn_rows(
    db: Session, generative_process_id: int
) -> tuple[GenerativeProcess, GenerativeSession]:
    """Load a chat turn's process and its session, checking the session is RAG.

    Parameters
    ----------
    db : Session
        Session the rows are read in.
    generative_process_id : int
        The turn being run.

    Returns
    -------
    tuple[GenerativeProcess, GenerativeSession]
        The process and the session it belongs to.

    Raises
    ------
    JobError
        If the process or its session is missing, or the session is not a RAG one.
    """
    generative_process = db.get(GenerativeProcess, generative_process_id)
    if not generative_process:
        raise JobError(f"Generative process {generative_process_id} not found in DB.")
    generative_session = db.get(GenerativeSession, generative_process.session_id)
    if not generative_session:
        raise JobError(f"Session {generative_process.session_id} not found in DB.")
    if generative_session.workflow_name != RAG_WORKFLOW_NAME:
        raise JobError(
            f"Session {generative_session.id} is run by "
            f"{generative_session.workflow_name}, not "
            f"{RAG_WORKFLOW_NAME}."
        )
    return generative_process, generative_session


def _run_cleanup_if_rebuilt(
    db: Session,
    component_registry: "ComponentRegistry",
    session_id: int,
    footprint_before: "IndexFootprint",
    model: RAGPipeline,
    rag_path: str | Path,
) -> None:
    """Run the post-index cleanup when a build changed the index, or left stale rows.

    A build adds chunk sets and bridges only when it creates something new, so a
    footprint that differs from the one taken before the build means the cleanup
    has work to do. A cleanup that failed earlier leaves stale rows behind a build
    that reused everything, so those are checked as well.

    Parameters
    ----------
    db : Session
        Session the cleanup runs in.
    component_registry : ComponentRegistry
        Component registry, passed through to the cleanup.
    session_id : int
        The generative session being built.
    footprint_before : IndexFootprint
        The session's footprint captured before the build.
    model : RAGPipeline
        The pipeline the build returned; its root retriever is the live index.
    rag_path : str | Path
        The RAG storage root (``RAG_PATH``).
    """
    footprint_after = capture_index_footprint(db, session_id)
    if footprint_after == footprint_before and not has_stale_index_rows(db, session_id):
        return
    run_post_index_cleanup(
        db,
        component_registry,
        session_id,
        model.retriever.get_id(),
        rag_path,
    )


def _build_turn_pipeline(
    db: Session,
    component_registry: "ComponentRegistry",
    config: Mapping[str, Any],
    generative_session: GenerativeSession,
) -> RAGPipeline:
    """Build the session's pipeline for one turn, then clean up after a rebuild.

    Parameters
    ----------
    db : Session
        Session the pipeline is built in.
    component_registry : ComponentRegistry
        Component registry used to resolve the stored components.
    config : Mapping[str, Any]
        Application configuration, which holds the ``RAG_PATH`` setting.
    generative_session : GenerativeSession
        The RAG session whose parameters describe the pipeline.

    Returns
    -------
    RAGPipeline
        The built pipeline.
    """
    # Whitelist-only: accept only known RAG pipeline keys.
    # Prompts live in their own table, so materialize them
    # back into the configuration before building the pipeline.
    if generative_session.parameters is None:
        raise JobError(f"Session {generative_session.id} has no stored parameters.")
    raw_params = PromptService(db, component_registry).materialize_session_parameters(
        generative_session.id,
        dict(generative_session.parameters),
    )
    extra_keys: set[str] = set(raw_params) - _RAG_PARAM_KEYS
    if extra_keys:
        log.debug("Filtered extra session parameter keys: %s", sorted(extra_keys))
    clean_params = filter_pipeline_params(raw_params, _RAG_PARAM_KEYS)
    pipeline_config = RAGPipelineConfig.from_kwargs(
        db=db,
        component_registry=component_registry,
        session_id=generative_session.id,
        env_RAG_path=config["RAG_PATH"],
        **clean_params,
    )
    setup_service = SetupService(db, component_registry, config["RAG_PATH"])
    # The build reuses the stored index unless its configuration changed. Only a
    # build that created rows can leave stale ones behind, so the cleanup runs
    # after such a build.
    footprint_before = capture_index_footprint(db, generative_session.id)
    model: RAGPipeline = setup_service.build_pipeline(pipeline_config)
    _run_cleanup_if_rebuilt(
        db,
        component_registry,
        generative_session.id,
        footprint_before,
        model,
        config["RAG_PATH"],
    )
    return model


def _load_history(
    db: Session, task: "BaseGenerativeTask", session_id: int, process_id: int
) -> list[tuple[str, str]]:
    """Build the conversation history from the finished turns before this one.

    A retried turn keeps its place in the conversation (#969), so later turns are
    not its history. Each prior answer is resolved by its row type, not its
    position, and a finished process with no message row is skipped.

    Parameters
    ----------
    db : Session
        Session the finished processes are read in.
    task : BaseGenerativeTask
        The task that knows how to read the message out of a process's output.
    session_id : int
        The generative session of the turn.
    process_id : int
        The turn being run; only processes with a lower id are history.

    Returns
    -------
    list[tuple[str, str]]
        ``(user message, assistant message)`` pairs, oldest first.
    """
    finished_processes: list[GenerativeProcess] = (
        db.query(GenerativeProcess)
        .filter(
            GenerativeProcess.session_id == session_id,
            GenerativeProcess.status == RunStatus.FINISHED,
            GenerativeProcess.id < process_id,
        )
        .order_by(GenerativeProcess.id)
        .all()
    )
    history: list[tuple[str, str]] = []
    for prior in finished_processes:
        message = task.extract_message_from_output(prior.output)
        if message is None:
            log.debug(
                "Skipping process %d from history: no %r output row.",
                prior.id,
                RAG_OUTPUT_MESSAGE_TYPE,
            )
            continue
        history.append((prior.input[0].data, message))
    return history


def _prepare_turn(
    db: Session,
    component_registry: "ComponentRegistry",
    config: Mapping[str, Any],
    generative_process_id: int,
) -> tuple[RAGPipeline, Any, int, "BaseGenerativeWorkflow"]:
    """Run the setup stage of a turn and mark the process as started.

    Builds the pipeline, prepares the input with the conversation history, and
    commits the started status. The caller generates with the returned pipeline.

    Parameters
    ----------
    db : Session
        Session the setup runs in.
    component_registry : ComponentRegistry
        Component registry used to resolve the stored components.
    config : Mapping[str, Any]
        Application configuration.
    generative_process_id : int
        The turn being run.

    Returns
    -------
    tuple[RAGPipeline, Any, int, BaseGenerativeWorkflow]
        The built pipeline, the prepared input, the process id and the workflow
        that saves the output.

    Raises
    ------
    JobError
        If the process or session is missing, or the session is not a RAG one.
    """
    generative_process, generative_session = _load_turn_rows(db, generative_process_id)
    model = _build_turn_pipeline(db, component_registry, config, generative_session)
    input_data = generative_process.input
    task: BaseGenerativeTask = component_registry[generative_session.task_name][
        "class"
    ]()
    workflow: BaseGenerativeWorkflow = component_registry[
        generative_session.workflow_name
    ]["class"]()
    history = _load_history(db, task, generative_session.id, generative_process.id)
    input_data = task.prepare_for_task(input_data, history=history)

    generative_process.set_status_as_started()
    generative_process.set_progress(None)
    db.commit()
    log.debug("Pipeline built and ready for process %d", generative_process_id)
    return model, input_data, generative_process.id, workflow


def _process_data_rows(
    output_data: Iterable[Any], process_id: int
) -> list[ProcessData]:
    """Turn the workflow's ``(data, type)`` output pairs into process rows.

    Parameters
    ----------
    output_data : Iterable[Any]
        The pairs the workflow produced.
    process_id : int
        The process the rows belong to.

    Returns
    -------
    list[ProcessData]
        One output row per pair, in order.

    Raises
    ------
    JobError
        If an item is not a ``(data, type)`` pair.
    """
    rows: list[ProcessData] = []
    for item in output_data:
        if not isinstance(item, tuple) or len(item) != 2:
            raise JobError("Output from task must be a list of tuples (data, type).")
        data, data_type = item
        rows.append(
            ProcessData(
                data=data,
                data_type=data_type,
                process_id=process_id,
                is_input=False,
            )
        )
    return rows


def _save_turn_output(
    db: Session,
    workflow: "BaseGenerativeWorkflow",
    output: Any,
    process_id: int,
    images_path: str | Path,
) -> None:
    """Save a generated answer and mark its process as finished.

    Parameters
    ----------
    db : Session
        Session the output is saved in.
    workflow : BaseGenerativeWorkflow
        The workflow that turns the raw generation into ``(data, type)`` pairs.
    output : Any
        The raw generation result.
    process_id : int
        The process that produced the output.
    images_path : str | Path
        The ``IMAGES_PATH`` setting, where generated images are written.

    Raises
    ------
    JobError
        If the process is missing, or the workflow output is malformed.
    """
    generative_process = db.get(GenerativeProcess, process_id)
    if not generative_process:
        raise JobError(f"Generative process {process_id} not found when saving output.")
    output_data = workflow.process_output(output, images_path=images_path)
    db.add_all(_process_data_rows(output_data, process_id))
    db.commit()

    db.refresh(generative_process)
    generative_process.set_progress(None)
    generative_process.set_status_as_finished()
    db.commit()
    log.debug("Output saved for process %d", process_id)


def _stage_error(prefix: str, error: Exception) -> JobError:
    """Log a stage failure and wrap it in a job error that carries the stage prefix.

    Parameters
    ----------
    prefix : str
        Human-readable stage description, e.g. ``"Error during RAG pipeline
        setup"``.
    error : Exception
        The exception that ended the stage. It is logged with its traceback.

    Returns
    -------
    JobError
        The job error to store and raise, built by :func:`_job_error`.
    """
    log.exception(error)
    return _job_error(prefix, error)


def _release_run_resources(failure: BaseException | None) -> None:
    """Release what a run held, once its failure has left the except block.

    The frame release runs first, then ``gc.collect()`` so ``empty_cache()`` can
    hand the freed blocks back to CUDA. Every step is best-effort and must not
    replace the failure that ended the run.

    Parameters
    ----------
    failure : BaseException | None
        The failure that ended the run, or ``None`` when the run completed.
    """
    if failure is not None:
        _release_frames(failure)
    gc.collect()
    _empty_accelerator_cache()


class RAGJob(BaseJob):
    """RAGJob handles the full RAG pipeline lifecycle as a background job."""

    @inject
    def set_status_as_delivered(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as delivered.

        Args:
            session_factory: Injected SQLAlchemy session factory.

        Raises:
            JobError: If the generative process does not exist or a DB error
                occurs.
        """
        generative_process_id: int = self.kwargs["generative_process_id"]

        with session_factory() as db:
            process: GenerativeProcess = db.get(
                GenerativeProcess, generative_process_id
            )
            if not process:
                raise JobError(
                    f"Generative process {generative_process_id} does not exist in DB."
                )
            try:
                process.set_status_as_delivered()
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)
                raise JobError("Internal database error") from e

    @inject
    def set_status_as_error(
        self, session_factory: "sessionmaker" = lambda di: di["session_factory"]
    ) -> None:
        """Set the status of the job as error.

        Args:
            session_factory: Injected SQLAlchemy session factory.
        """
        generative_process_id: int = self.kwargs.get("generative_process_id")
        if generative_process_id is None:
            log.warning(
                "Cannot set error status: generative_process_id is missing from kwargs"
            )
            return

        with session_factory() as db:
            process: GenerativeProcess = db.get(
                GenerativeProcess, generative_process_id
            )
            if not process:
                return
            try:
                process.set_status_as_error()
                process.set_progress(None)
                db.commit()
            except exc.SQLAlchemyError as e:
                log.exception(e)

    @inject
    def _fail(
        self,
        error: JobError,
        session_factory: "sessionmaker" = lambda di: di["session_factory"],
    ) -> None:
        """Mark the turn as failed and store the error as its output (#969).

        The chat shows the stored detail in the failed turn's error bubble, as
        it does for a plain chat turn. Best-effort: a database failure here is
        logged and must never replace the error that ended the job.

        Args:
            error: The error that ended the job; its message is the detail.
            session_factory: Injected SQLAlchemy session factory.
        """
        generative_process_id = self.kwargs.get("generative_process_id")
        try:
            with session_factory() as db:
                process = db.get(GenerativeProcess, generative_process_id)
                fail_process(db, process, str(error))
        except exc.SQLAlchemyError as e:
            log.exception(e)

    @inject
    def get_job_name(self) -> str:
        """Get a descriptive name for the job.

        Returns:
            A human-readable name including the session name if available,
            otherwise a fallback like ``"RAG Process #<id>"``.
        """
        generative_process_id = self.kwargs.get("generative_process_id")
        if not generative_process_id:
            return "RAG Process"

        session_factory = di["session_factory"]

        try:
            with session_factory() as db:
                process: GenerativeProcess = db.get(
                    GenerativeProcess, generative_process_id
                )
                if process:
                    session: GenerativeSession = db.get(
                        GenerativeSession, process.session_id
                    )
                    if session and session.name:
                        return f"RAG: {session.name}"
                    return f"RAG Process #{generative_process_id}"
        except Exception as e:
            log.exception(f"Error getting job name: {e}")

        return f"RAG Process #{generative_process_id}"

    def _run_setup(
        self,
        session_factory: "sessionmaker",
        component_registry: "ComponentRegistry",
        config: Mapping[str, Any],
        generative_process_id: int,
    ) -> tuple[RAGPipeline, Any, int, "BaseGenerativeWorkflow"]:
        """Run session 1: load, build, prepare and mark the turn as started.

        A ``JobError`` is stored on the process and re-raised unchanged. Any
        other exception is logged, wrapped with the setup prefix, stored and
        raised.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory for the short-lived setup session.
        component_registry : ComponentRegistry
            Component registry used to resolve the stored components.
        config : Mapping[str, Any]
            Application configuration.
        generative_process_id : int
            The turn being run.

        Returns
        -------
        tuple[RAGPipeline, Any, int, BaseGenerativeWorkflow]
            The built pipeline, the prepared input, the process id and the
            workflow that saves the output.

        Raises
        ------
        JobError
            If the setup fails.
        """
        try:
            with session_factory() as db:
                return _prepare_turn(
                    db, component_registry, config, generative_process_id
                )
        except JobError as e:
            self._fail(e)
            raise
        except Exception as e:
            error = _stage_error("Error during RAG pipeline setup", e)
            self._fail(error)
            raise error from e

    def _run_generation(
        self,
        session_factory: "sessionmaker",
        model: RAGPipeline,
        input_data: Any,
        process_id: int,
    ) -> Any:
        """Run the generation stage, with no database session held open.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory for the progress reporter's short-lived sessions.
        model : RAGPipeline
            The pipeline built by the setup stage.
        input_data : Any
            The prepared input the pipeline generates from.
        process_id : int
            The process whose live progress the reporter writes.

        Returns
        -------
        Any
            The raw generation result, saved by the output stage.

        Raises
        ------
        JobError
            If the generation fails.
        """
        reporter = _make_progress_reporter(session_factory, process_id)
        try:
            output: Any = model.generate(input_data, progress_callback=reporter)
            log.debug("Generation completed for process %d", process_id)
        except Exception as e:
            error = _stage_error("Error during RAG pipeline execution", e)
            self._fail(error)
            raise error from e
        return output

    def _run_save(
        self,
        session_factory: "sessionmaker",
        workflow: "BaseGenerativeWorkflow",
        output: Any,
        process_id: int,
        config: Mapping[str, Any],
    ) -> None:
        """Run session 2: save the generated output and mark the turn finished.

        Parameters
        ----------
        session_factory : sessionmaker
            Factory for the short-lived save session.
        workflow : BaseGenerativeWorkflow
            The workflow that turns the raw generation into ``(data, type)`` pairs.
        output : Any
            The raw generation result.
        process_id : int
            The process that produced the output.
        config : Mapping[str, Any]
            Application configuration, which holds the ``IMAGES_PATH`` setting.

        Raises
        ------
        JobError
            If the output cannot be saved.
        """
        try:
            with session_factory() as db:
                _save_turn_output(
                    db, workflow, output, process_id, config["IMAGES_PATH"]
                )
        except Exception as e:
            error = _stage_error("Error processing and saving RAG generation output", e)
            self._fail(error)
            raise error from e

    @inject
    def run(self) -> None:
        """Execute the full RAG pipeline lifecycle as a background job.

        Uses two separate DB sessions to avoid holding a connection open
        during LLM inference (which may take minutes):
        - **Session 1**: load data, build pipeline, prepare input, mark as started.
        - **(no session)**: LLM inference via ``model.generate()``.
        - **Session 2**: save output, mark as finished.

        Cleanup (drop the model reference, release traceback frames, garbage
        collect and clear the CUDA cache) runs after the body on every path,
        including setup, generation and save failures. The original failure is
        then re-raised unchanged.

        Raises:
            JobError: If any stage of execution fails.
        """
        component_registry = di["component_registry"]
        session_factory = di["session_factory"]
        config = di["config"]

        if "generative_process_id" not in self.kwargs:
            raise JobError("RAGJob requires 'generative_process_id' in kwargs.")

        generative_process_id: int = self.kwargs["generative_process_id"]
        model = None
        failure: BaseException | None = None

        # The whole body is captured instead of re-raised immediately: while a
        # failure is propagating its traceback still pins the model (and the
        # half-built pipeline), so cleanup must run after the except block.
        try:
            model, input_data, process_id, workflow = self._run_setup(
                session_factory, component_registry, config, generative_process_id
            )
            output = self._run_generation(
                session_factory, model, input_data, process_id
            )
            self._run_save(session_factory, workflow, output, process_id, config)
        except BaseException as error:
            failure = error

        # Cleanup runs here, after the except block, because while an exception
        # is propagating its traceback still references the model and pipeline.
        model = None
        _release_run_resources(failure)
        if failure is not None:
            raise failure
