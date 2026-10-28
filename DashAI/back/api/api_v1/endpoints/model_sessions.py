import logging
from typing import TYPE_CHECKING, Optional, Union

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.exceptions import HTTPException
from kink import di, inject
from pydantic import ValidationError
from sqlalchemy import exc, select

from DashAI.back.api.api_v1.schemas.model_sessions_params import (
    ColumnsValidationParams,
    ModelSessionBulkDeleteParams,
    ModelSessionParams,
    PreprocessingStructureParams,
    SessionExportParams,
)
from DashAI.back.api.utils import (
    offered_components,
    remove_run_files,
    run_file_paths,
    task_or_http_error,
)
from DashAI.back.core.schema_fields.utils import schema_placeholder_defaults
from DashAI.back.dependencies.database.models import Dataset, ModelSession, Run
from DashAI.back.job.preprocessing_job import PreprocessingJob
from DashAI.back.preprocessing.column_ref import ConverterSequence
from DashAI.back.preprocessing.structure import (
    StructureError,
    infer_structure,
    resolve_state_refs,
)
from DashAI.back.splitters.splits_payload import (
    DEFAULT_SPLITTER_NAME,
    META_KEYS,
    normalize_splits_payload,
)
from DashAI.back.tasks.session_roles import SessionColumnRoles, session_roles

if TYPE_CHECKING:
    from sqlalchemy.orm import sessionmaker

    from DashAI.back.dependencies.job_queues import BaseJobQueue
    from DashAI.back.dependencies.registry import ComponentRegistry
    from DashAI.back.tasks.base_task import BaseTask


logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
@inject
async def get_model_sessions(
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Retrieve a list of the stored model sessions in the database.

    Parameters
    ----------
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.


    Returns
    -------
    List[dict]
        A list of dict containing model sessions.
    """
    with session_factory() as db:
        try:
            all_model_sessions = db.query(ModelSession).all()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        return all_model_sessions


@router.get("/{model_session_id}")
@inject
async def get_model_session(
    model_session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Retrieve the model session associated with the provided ID.

    Parameters
    ----------
    model_session_id : int
        ID of the model session to retrieve.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    JSON
        JSON with the specified model session id.
    """
    with session_factory() as db:
        try:
            model_session = db.get(ModelSession, model_session_id)
            if not model_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model session not found",
                )
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
        return model_session


def _load_sample_dataset(db, dataset_id: int):
    """Load the first rows of a dataset, enough for its columns and types.

    Parameters
    ----------
    db : Session
        An open database session.
    dataset_id : int
        The dataset to load.

    Returns
    -------
    DashAIDataset
        At most 5 rows of the dataset, with every column and its type.

    Raises
    ------
    HTTPException
        404 if the dataset is not registered.
    """
    import os

    import pyarrow as pa
    import pyarrow.ipc as ipc

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

    dataset = db.get(Dataset, dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )
    data_filepath = os.path.join(f"{dataset.file_path}/dataset", "data.arrow")
    with pa.OSFile(data_filepath, "rb") as source:
        reader = ipc.open_file(source)
        batch = reader.get_batch(0)
        sample_batch = batch.slice(0, min(5, batch.num_rows))
    return DashAIDataset(pa.Table.from_batches([sample_batch]))


def _ref_label(label: str) -> str:
    """A ref as ``resolve_state_refs`` labels it, said in words.

    A whole group is labelled by its step index ("0"), a slot of one by
    "step:slot", and anything else by its column name.
    """
    step, _, slot = label.partition(":")
    if step.isdigit():
        number = int(step) + 1
        if slot:
            return f"the {slot} output of step {number}"
        return f"the output of step {number}"
    return repr(label)


def _ref_problem(role_name: str, error: StructureError) -> str:
    """The message of a role ref that does not resolve after the preprocessing."""
    params = error.message.params
    if error.message.code == "target_in_scope":
        return (
            f"The {role_name!r} role takes the column {params.get('column')!r}, "
            "which is protected from the preprocessing."
        )
    if error.message.code == "missing_ref":
        return (
            f"The {role_name!r} role takes {_ref_label(str(params.get('ref')))}, "
            "which does not exist after the preprocessing."
        )
    return error.message.code


def _roles_problem(
    task: "BaseTask", roles, sample, steps, component_registry
) -> Optional[str]:
    """What is structurally wrong with a session's columns for its task.

    The roles are checked at the final stage, the one the model reads: a role
    the preprocessing may transform is checked against the chain's estimated
    structure when there are steps, every other role against the types of
    the original columns.

    Parameters
    ----------
    task : BaseTask
        The session's task.
    roles : mapping
        Role name to the role's column refs.
    sample : DashAIDataset
        A few rows of the session's dataset, for its column names and types.
    steps : list of ConverterStep
        The session's preprocessing chain, possibly empty.
    component_registry : ComponentRegistry
        Resolves the chain's converters.

    Returns
    -------
    str or None
        The problem, worded for the user, or None when the columns fit.
    """
    try:
        task.check_role_names(roles)
    except ValueError as e:
        return str(e)

    declared = task.column_roles()
    for role in declared:
        refs = roles.get(role.name) or []
        if not role.transformable and any(ref.kind == "group" for ref in refs):
            return (
                f"The {role.name!r} role of {type(task).__name__} is protected "
                "from the preprocessing: it takes original columns only."
            )
    if not steps and any(ref.kind == "group" for r in roles.values() for ref in r):
        # A converter's output only has a type through the chain's estimated
        # structure, which needs the preprocessing steps.
        return "References to converter outputs need the preprocessing steps."

    protected = [
        ref.name
        for role in declared
        if not role.transformable
        for ref in roles.get(role.name) or []
    ]
    structure = None
    if steps:
        structure = infer_structure(
            dataset_types=sample.types,
            candidates=list(sample.column_names),
            target=protected,
            steps=steps,
            component_registry=component_registry,
        )
        if not structure.valid:
            return "The preprocessing chain has an invalid step."

    for role in declared:
        refs = list(roles.get(role.name) or [])
        try:
            if structure is None or not role.transformable:
                task.validate_role(role.name, [ref.name for ref in refs], sample.types)
            else:
                items = resolve_state_refs(refs, structure.final, set(protected))
                task.validate_estimated_role(
                    role.name,
                    [
                        (item.type, 1 if item.kind == "column" else item.count)
                        for item in items
                    ],
                )
        except StructureError as e:
            return _ref_problem(role.name, e)
        except KeyError as e:
            return f"Column {e.args[0]!r} is not in the dataset."
        except (TypeError, ValueError) as e:
            return str(e)
    return None


@router.post("/preprocessing/structure")
@inject
async def get_preprocessing_structure(
    params: PreprocessingStructureParams,
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Estimate the dataset structure after every step of a converter chain.

    Read only: nothing is fit and nothing is stored. The session wizard calls
    it on every change to the chain, to offer only columns that exist at each
    step and to flag steps that cannot work.

    Parameters
    ----------
    params : PreprocessingStructureParams
        The dataset, the candidate and target columns, and the chain.

    Returns
    -------
    StructureResult
        The state after every step, their errors and warnings, and the final
        state.
    """
    task = task_or_http_error(params.task_name, component_registry)
    with session_factory() as db:
        try:
            sample = _load_sample_dataset(db, params.dataset_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e
    # The roles the preprocessing may transform are what feeds the chain; the
    # protected ones never enter it and no step may reference them.
    candidates, protected = [], []
    for role in task.column_roles():
        side = candidates if role.transformable else protected
        for name in params.column_roles.get(role.name, []):
            if name not in side:
                side.append(name)
    return infer_structure(
        dataset_types=sample.types,
        candidates=candidates,
        target=protected,
        steps=params.steps,
        component_registry=component_registry,
    )


@router.post("/validation")
@inject
async def validate_columns(
    params: ColumnsValidationParams,
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Validate if dataset columns are compatible with a task.

    The same structural check a new session goes through (``_roles_problem``):
    every role is one the task declares and gets columns of its types and in
    its number, at the final stage. With `preprocessing`, a role the
    preprocessing may transform is checked against the chain's estimated
    structure.
    """
    with session_factory() as db:
        try:
            minimal_dataset = _load_sample_dataset(db, params.dataset_id)
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    task = task_or_http_error(params.task_name, component_registry)

    column_names = minimal_dataset.column_names
    io = task.io_columns(params.column_roles)
    input_refs = list(io.inputs)
    group_refs = [ref for ref in input_refs if ref.kind == "group"]
    inputs_names = [ref.name for ref in input_refs if ref.kind == "raw"]
    outputs_names = [ref.name for ref in io.outputs]

    if not group_refs and len(inputs_names + outputs_names) > len(column_names):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Column index out of range",
        )

    problem = _roles_problem(
        task,
        params.column_roles,
        minimal_dataset,
        params.preprocessing or [],
        component_registry,
    )
    if problem is not None:
        return {"dataset_status": "invalid", "error": problem}
    return {"dataset_status": "valid"}


def _validate_evaluation_strategy(
    task_name: str, evaluation_strategy: str, component_registry: "ComponentRegistry"
) -> type:
    """Check that a session's evaluation strategy is one its task offers.

    The wizard lists only the strategies the registry relates to the task, and
    this asks the same registry the same question, so a session the front
    builds always passes. What it stops is a session put together by hand with
    a strategy its task never offered: one that carves nothing on a task with
    a target, which would train without ever reading the target, or a holdout
    on a task without one. A run relies on this pairing to know from the
    strategy alone which units to chain.

    Parameters
    ----------
    task_name : str
        The session's task.
    evaluation_strategy : str
        The session's evaluation strategy.
    component_registry : ComponentRegistry
        Registry that relates tasks to the strategies they offer.

    Returns
    -------
    type
        The strategy class, so the caller can read what it declares.

    Raises
    ------
    HTTPException
        If the task is not registered, or the strategy is not one it offers.
    """
    if task_name not in component_registry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Task {task_name} does not exist in the registry.",
        )

    offered = offered_components(component_registry, task_name, "EvaluationStrategy")
    if evaluation_strategy not in offered:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Evaluation strategy {evaluation_strategy!r} is not available "
                f"for task {task_name}. Available strategies: {offered}."
            ),
        )
    return component_registry[evaluation_strategy]["class"]


def _validate_splits(
    splits: str,
    task_name: str,
    strategy_class: type,
    component_registry: "ComponentRegistry",
) -> None:
    """Validate a splits payload against its task, its strategy and its schema.

    In this order, after resolving the splitter the payload names (or the
    default one, for a payload that names none):

    - the splitter is one the task offers. The wizard lists only those, and
      this asks the registry the same question, so what it stops is a session
      put together by hand: a temporal holdout on a regression runs without a
      word, and the default holdout shuffles a task that never offered it;
    - its ``PARTITIONING`` is the one the strategy takes. A run prepares with
      the unit the splitter's partitioning picks and fits with the unit the
      strategy's kind picks, and the two read different context keys;
    - its schema accepts the payload. Any parameter the caller left out is
      filled with the schema placeholder, which is the value the frontend form
      would have submitted, so a manual split (which carries row indexes
      instead of proportions) validates too.

    Parameters
    ----------
    splits : str
        The splits payload, serialized as JSON.
    task_name : str
        The session's task, already known to be registered.
    strategy_class : type
        The session's evaluation strategy, already validated against the task.
    component_registry : ComponentRegistry
        Registry used to resolve the splitter and the splitters the task
        offers.

    Raises
    ------
    HTTPException
        If the payload is not valid JSON, names a splitter that is not
        registered or that the task does not offer, names one of a shape the
        strategy does not take, or carries parameters the splitter schema
        rejects.
    """
    import json

    try:
        payload = json.loads(splits)
        splits_data = normalize_splits_payload(payload)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"splits is not a valid JSON object: {e}",
        ) from e

    splitter_name = splits_data.get("splitter_name")
    if splitter_name not in component_registry:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Splitter {splitter_name} does not exist in the registry.",
        )

    offered = offered_components(component_registry, task_name, "Splitter")
    if splitter_name not in offered:
        named = isinstance(payload, dict) and isinstance(
            payload.get("splitter_name"), str
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Splitter {splitter_name!r} is not available for task "
                f"{task_name}. Available splitters: {offered}."
                if named
                else f"splits names no splitter, and the default, "
                f"{DEFAULT_SPLITTER_NAME}, is not available for task "
                f"{task_name}. Available splitters: {offered}."
            ),
        )

    splitter_class = component_registry[splitter_name]["class"]
    taken = getattr(strategy_class, "SPLITTER_PARTITIONING", "holdout")
    partitioning = getattr(splitter_class, "PARTITIONING", "holdout")
    if partitioning != taken:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Evaluation strategy {strategy_class.__name__} takes a {taken!r} "
                f"splitter, but {splitter_name} is a {partitioning!r} splitter."
            ),
        )
    parameters = {
        key: value for key, value in splits_data.items() if key not in META_KEYS
    }
    try:
        splitter_class.SCHEMA.model_validate(
            {**schema_placeholder_defaults(splitter_class), **parameters}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid configuration for splitter {splitter_name}: {e}",
        ) from e


def _validate_splits_size(
    splits: str, count_rows, component_registry: "ComponentRegistry"
) -> None:
    """Refuse a dataset too short for the session's splitter.

    Runs after ``_validate_splits``, so the payload parses and names a
    registered splitter. Most splitters carve any number of rows; a backtest
    needs enough steps for its windows, and saying so here beats a run that
    fails on it.

    Parameters
    ----------
    splits : str
        The splits payload, serialized as JSON.
    count_rows : Callable[[], int]
        How many rows the dataset has. Called only for a splitter that has a
        size to check, because counting may read the dataset.
    component_registry : ComponentRegistry
        Registry used to resolve the splitter.

    Raises
    ------
    HTTPException
        422 with the splitter's explanation.
    """
    import json

    from DashAI.back.splitters.base_splitter import BaseSplitter

    splits_data = normalize_splits_payload(json.loads(splits))
    splitter_class = component_registry[splits_data["splitter_name"]]["class"]
    # Only a splitter that has a size to check is built here: the others
    # accept any count, and building them would only risk a constructor that
    # needs what a run gives it.
    if splitter_class.validate_size is BaseSplitter.validate_size:
        return
    parameters = {
        key: value for key, value in splits_data.items() if key not in META_KEYS
    }
    splitter = splitter_class(
        {**schema_placeholder_defaults(splitter_class), **parameters}
    )
    try:
        splitter.validate_size(count_rows())
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e


def _row_count(dataset: Dataset, data_filepath: str) -> int:
    """How many rows a dataset has, without reading them if it can.

    The dataset's own ``total_rows`` when it has one: the dataset job writes
    it and every edit of the data rewrites it. A dataset from before the
    column was filled is counted from the file, memory mapped, so only the
    headers of its batches are read.
    """
    if dataset.total_rows is not None:
        return dataset.total_rows

    import pyarrow as pa
    import pyarrow.ipc as ipc

    with pa.memory_map(data_filepath, "r") as source:
        reader = ipc.open_file(source)
        return sum(
            reader.get_batch(i).num_rows for i in range(reader.num_record_batches)
        )


def _validate_roles_for_task(
    db, model_session: ModelSession, task_name: str, component_registry
) -> None:
    """Check the session's stored columns against the task it is moving to.

    Raises
    ------
    HTTPException
        422 naming the task and what does not fit.
    """
    task = task_or_http_error(task_name, component_registry)
    roles = session_roles(model_session, task).refs()
    steps = ConverterSequence.model_validate(
        model_session.preprocessing or {"steps": []}
    ).steps
    problem = _roles_problem(
        task,
        roles,
        _load_sample_dataset(db, model_session.dataset_id),
        steps,
        component_registry,
    )
    if problem is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"The session's columns do not fit task {task_name}: {problem}",
        )


def _validate_runs_for_task(
    db, model_session_id: int, task_name: str, component_registry: "ComponentRegistry"
) -> None:
    """Check that every run of a session has a model the new task offers.

    A change of task keeps the session's runs, and a run whose model the task
    does not offer is one the run API would have refused. Rather than deleting
    or flagging those runs, the change is refused and the runs are named, so
    the user learns about it and decides: changing the task of a session that
    already trained something is rare.

    Parameters
    ----------
    db : Session
        The open database session.
    model_session_id : int
        The session whose task changes.
    task_name : str
        The new task, already known to be registered.
    component_registry : ComponentRegistry
        Registry that relates tasks to the models they offer.

    Raises
    ------
    HTTPException
        If any run's model is not offered by the new task.
    """
    offered = offered_components(component_registry, task_name, "Model")
    runs = db.execute(
        select(Run).where(Run.model_session_id == model_session_id).order_by(Run.id)
    ).scalars()
    affected = [run for run in runs if run.model_name not in offered]
    if affected:
        named = ", ".join(
            f"{run.name!r} (id {run.id}, {run.model_name})" for run in affected
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Task {task_name} does not offer the model of these runs of the "
                f"session: {named}. Delete them or keep the current task."
            ),
        )


def _validate_empty_splits(splits: str, evaluation_strategy: str) -> None:
    """Check that a session whose strategy carves nothing sends no splits.

    Such a strategy takes no splitter, so any payload would be stored and never
    used, while the front still reads it back to decide which partitions the
    session has. Only an empty JSON object is accepted.

    Parameters
    ----------
    splits : str
        The splits payload, serialized as JSON.
    evaluation_strategy : str
        The session's evaluation strategy, named in the error.

    Raises
    ------
    HTTPException
        If the payload is not valid JSON or is not an empty object.
    """
    import json

    try:
        splits_data = json.loads(splits)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"splits is not a valid JSON object: {e}",
        ) from e

    if splits_data != {}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Evaluation strategy {evaluation_strategy} takes no splitter, "
                f"so splits must be an empty object, got {splits}."
            ),
        )


# A training-only resampler runs twice (PreprocessingJob and ModelJob replay
# the chain), so both runs must draw the same rows.
DEFAULT_RESAMPLING_SEED = 42


def _with_resampling_seeds(steps, component_registry):
    """Give every training-only resampling step without a seed a fixed one.

    Stored in the step's params, so it is visible in the session info. A
    seed the user chose is kept.

    Parameters
    ----------
    steps : list of ConverterStep
        The session's preprocessing steps, as submitted.
    component_registry : ComponentRegistry
        Resolves each step's converter class.

    Returns
    -------
    list of ConverterStep
        The steps, with `random_state` filled in where it was missing.
    """
    seeded = []
    for step in steps:
        converter_class = (
            component_registry[step.converter]["class"]
            if step.converter in component_registry
            else None
        )
        needs_seed = (
            converter_class is not None
            and getattr(converter_class, "ROWS_APPLY_TO", None) == "train"
            and step.params.get("random_state") is None
        )
        if needs_seed:
            step = step.model_copy(
                update={
                    "params": {**step.params, "random_state": DEFAULT_RESAMPLING_SEED}
                }
            )
        seeded.append(step)
    return seeded


def _check_preprocessing_structure(
    db, params, sequence, input_column_refs, output_columns, component_registry
) -> None:
    """Reject a session whose chain or inputs cannot work, before creating it.

    Without this, the session would be created and its PreprocessingJob
    would only fail afterwards, with an error like a bare missing column
    name.

    Raises
    ------
    HTTPException
        422 with the estimated structure when a step is invalid, or with the
        error when an input ref points at something the chain does not
        produce (or consumed).
    """
    sample = _load_sample_dataset(db, params.dataset_id)
    structure = infer_structure(
        dataset_types=sample.types,
        candidates=list(sample.column_names),
        target=output_columns,
        steps=sequence.steps,
        component_registry=component_registry,
    )
    if not structure.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "The preprocessing chain has an invalid step.",
                "structure": structure.model_dump(mode="json"),
            },
        )
    try:
        resolve_state_refs(input_column_refs, structure.final, set(output_columns))
    except StructureError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "An input column does not exist after preprocessing.",
                "error": e.message.model_dump(mode="json"),
            },
        ) from e


@router.post("/", status_code=status.HTTP_201_CREATED)
@inject
async def create_model_session(
    params: ModelSessionParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    job_queue: "BaseJobQueue" = Depends(lambda: di["job_queue"]),
):
    """Create a new model session.

    Parameters
    ----------
    params : ModelSessionParams
        The new model session parameters.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry used to resolve the splitter named in the splits payload.

    Returns
    -------
    ModelSession
        The created model session.

    Raises
    ------
    HTTPException
        If the splits payload is not valid for the selected splitter.
    HTTPException
        If the dataset with id dataset_id is not registered in the DB.
    """
    import os

    import pyarrow as pa
    import pyarrow.ipc as ipc

    strategy_class = _validate_evaluation_strategy(
        params.task_name, params.evaluation_strategy, component_registry
    )
    if getattr(strategy_class, "KIND", "holdout") == "full":
        # A strategy that carves nothing takes no splitter, so its splits
        # payload must be empty, and no session preprocessing, which is fitted
        # once per partition.
        _validate_empty_splits(params.splits, params.evaluation_strategy)
        if params.preprocessing:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Evaluation strategy {params.evaluation_strategy} does not "
                    "take session preprocessing: it is fitted per partition, "
                    "and this strategy makes none."
                ),
            )
    else:
        _validate_splits(
            params.splits, params.task_name, strategy_class, component_registry
        )

    sequence = ConverterSequence(
        steps=_with_resampling_seeds(params.preprocessing, component_registry)
    )
    try:
        sequence.validate_scopes()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        ) from e
    has_preprocessing = len(sequence.steps) > 0

    # The task translates the roles it was given into the model's inputs
    # and outputs, which the checks below read.
    task = task_or_http_error(params.task_name, component_registry)
    if has_preprocessing and not any(
        role.transformable for role in task.column_roles()
    ):
        # Session preprocessing transforms the columns of the roles that
        # allow it, and fits once per partition. A task none of whose roles
        # allow it has nothing for the steps to feed, and partitions that are
        # not rows: single-series forecasting until its exogenous role.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"{params.task_name} takes no preprocessing: none of its column "
                "roles can be transformed. Transform the dataset in a notebook "
                "instead."
            ),
        )
    roles = {name: list(refs) for name, refs in params.column_roles.items() if refs}
    io = task.io_columns(roles)
    input_column_refs = list(io.inputs)
    raw_inputs = [ref.name for ref in input_column_refs if ref.kind == "raw"]
    output_columns = [ref.name for ref in io.outputs]

    if has_preprocessing and not input_column_refs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "column_roles has to give the model's inputs when preprocessing "
                "steps are provided"
            ),
        )

    column_roles = SessionColumnRoles.from_refs(roles)

    with session_factory() as db:
        try:
            dataset = db.get(Dataset, params.dataset_id)
            if not dataset:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found"
                )
            dataset_path = f"{dataset.file_path}/dataset"
            data_filepath = os.path.join(dataset_path, "data.arrow")

            with pa.OSFile(data_filepath, "rb") as source:
                reader = ipc.open_file(source)
                schema = reader.schema
                column_names = schema.names

            if getattr(strategy_class, "KIND", "holdout") != "full":
                _validate_splits_size(
                    params.splits,
                    lambda: _row_count(dataset, data_filepath),
                    component_registry,
                )

            if has_preprocessing:
                _check_preprocessing_structure(
                    db,
                    params,
                    sequence,
                    input_column_refs,
                    output_columns,
                    component_registry,
                )

            # When preprocessing is configured, some inputs are converter
            # outputs that only exist once PreprocessingJob has fitted the
            # chain, so they cannot be counted against the raw dataset.
            if not has_preprocessing and len(raw_inputs + output_columns) > len(
                column_names
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Column index out of range",
                )

            problem = _roles_problem(
                task,
                roles,
                _load_sample_dataset(db, params.dataset_id),
                sequence.steps,
                component_registry,
            )
            if problem is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=problem
                )

            model_session = ModelSession(
                dataset_id=params.dataset_id,
                task_name=params.task_name,
                name=params.name,
                train_metrics=params.train_metrics,
                validation_metrics=params.validation_metrics,
                test_metrics=params.test_metrics,
                evaluation_strategy=params.evaluation_strategy,
                splits=params.splits,
                preprocessing=sequence.model_dump(mode="json"),
                column_roles=column_roles.to_stored(),
                preprocessing_status="pending" if has_preprocessing else "ready",
            )
            db.add(model_session)
            db.commit()
            db.refresh(model_session)

            if has_preprocessing:
                job_id = job_queue.put(
                    PreprocessingJob(model_session_id=model_session.id)
                ).id
                model_session.preprocessing_job_id = str(job_id)
                db.commit()
                db.refresh(model_session)

            return model_session
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Model session with name '{params.name}' already exists.",
            ) from e
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.delete("/")
@inject
async def delete_model_sessions(
    params: ModelSessionBulkDeleteParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete multiple model sessions, in a single transaction.

    Parameters
    ----------
    params : ModelSessionBulkDeleteParams
        The IDs of the model sessions to delete. IDs that do not match an
        existing model session are silently skipped rather than failing the
        whole request.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Response with code 204 NO_CONTENT
    """
    with session_factory() as db:
        try:
            paths_to_clean = []
            for model_session_id in params.ids:
                model_session = db.get(ModelSession, model_session_id)
                if not model_session:
                    continue
                paths_to_clean += run_file_paths(model_session.runs)
                db.delete(model_session)

            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    # The files of the runs the cascade deleted, once the delete committed.
    remove_run_files(paths_to_clean)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{model_session_id}")
@inject
async def delete_model_session(
    model_session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """Delete the model session associated with the provided ID from the database.

    Parameters
    ----------
    model_session_id : int
        ID of the model session to be deleted.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.

    Returns
    -------
    Response with code 204 NO_CONTENT
    """
    with session_factory() as db:
        try:
            model_session = db.get(ModelSession, model_session_id)
            if not model_session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model session not found",
                )

            # Snapshot the on-disk paths of the runs that the FK cascade is
            # about to delete, so they can be cleaned up after the commit.
            runs = db.query(Run).filter(Run.model_session_id == model_session_id).all()
            paths_to_clean = run_file_paths(runs)

            db.delete(model_session)
            db.commit()
        except exc.SQLAlchemyError as e:
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e

    # Best-effort disk cleanup, done only once the DB delete has committed:
    # a cleanup failure here must not undo an otherwise-successful deletion.
    remove_run_files(paths_to_clean)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{model_session_id}")
@inject
async def update_model_session(
    model_session_id: int,
    request: Request,
    task_name: Union[str, None] = None,
    name: Union[str, None] = None,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Update the model session associated with the provided ID.

    Parameters
    ----------
    model_session_id : int
        ID of the model session to update.
    session_factory : Callable[..., ContextManager[Session]]
        A factory that creates a context manager that handles a SQLAlchemy session.
        The generated session can be used to access and query the database.
    component_registry : ComponentRegistry
        Registry used to check that a new task still offers the session's
        evaluation strategy.

    Returns
    -------
    Dict
        A dictionary containing the updated model session record.

    Raises
    ------
    HTTPException
        422 when the request names a ``dataset_id``. A session is one
        dataset: its roles, splits, fitted preprocessing and runs all point
        into it, so working on another dataset is another session.
    """
    if "dataset_id" in request.query_params:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "The dataset of a model session cannot change: its columns, "
                "splits, preprocessing and runs belong to it. To work on "
                "another dataset, create a new session."
            ),
        )
    with session_factory() as db:
        try:
            model_session = db.get(ModelSession, model_session_id)
            if model_session is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Model session not found",
                )

            # Validate name if provided
            if name is not None:
                if not name or not name.strip():
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Name cannot be empty",
                    )

                new_name = name.strip()

                # Check if name is different from current name
                if new_name != model_session.name:
                    # Check if name already exists
                    exists = db.execute(
                        select(ModelSession.id).where(
                            ModelSession.name == new_name,
                            ModelSession.id != model_session_id,
                        )
                    ).scalar()
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail="Model session name already exists",
                        )
                    setattr(model_session, "name", new_name)

            if task_name:
                # The stored strategy and splitter must still be ones the new
                # task offers, the same checks a new session goes through.
                if task_name != model_session.task_name:
                    strategy_class = _validate_evaluation_strategy(
                        task_name, model_session.evaluation_strategy, component_registry
                    )
                    if getattr(strategy_class, "KIND", "holdout") != "full":
                        _validate_splits(
                            model_session.splits,
                            task_name,
                            strategy_class,
                            component_registry,
                        )
                    _validate_runs_for_task(
                        db, model_session_id, task_name, component_registry
                    )
                    _validate_roles_for_task(
                        db, model_session, task_name, component_registry
                    )
                setattr(model_session, "task_name", task_name)

            if task_name or name:
                db.commit()
                db.refresh(model_session)
                return model_session
            else:
                raise HTTPException(
                    status_code=status.HTTP_304_NOT_MODIFIED,
                    detail="Record not modified",
                )
        except HTTPException:
            raise
        except exc.IntegrityError as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Model session name already exists",
            ) from e
        except exc.SQLAlchemyError as e:
            db.rollback()
            log.exception(e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal database error",
            ) from e


@router.post("/import", status_code=status.HTTP_201_CREATED)
@inject
async def import_model_session(
    file: UploadFile = File(...),
    accept_language: str | None = Header(default=None),
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
    config=Depends(lambda: di["config"]),
    job_queue: "BaseJobQueue" = Depends(lambda: di["job_queue"]),
):
    """Create a new session, its dataset and runs from an uploaded ``.dashai``.

    Raises
    ------
    HTTPException
        400 if the file is not a usable DashAI session, 409 if it needs a
        newer DashAI or a missing plugin, 500 on any other failure.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from fastapi.concurrency import run_in_threadpool

    from DashAI.back.model_package.manifest import (
        MissingPluginError,
        ModelPackageError,
        UnsupportedPackageFormatError,
    )
    from DashAI.back.session_package.load import import_session_package

    workdir = Path(tempfile.mkdtemp(prefix="dashai-upload-"))
    try:
        upload = workdir / "session.dashai"
        with open(upload, "wb") as handle:
            shutil.copyfileobj(file.file, handle)
        return await run_in_threadpool(
            import_session_package,
            upload,
            session_factory,
            component_registry,
            config,
            job_queue,
            (accept_language or "en").split("-")[0].lower(),
        )
    except (UnsupportedPackageFormatError, MissingPluginError) as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except ModelPackageError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error importing the session",
        ) from e
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


@router.get("/{model_session_id}/export/preview")
@inject
async def get_session_export_preview(
    model_session_id: int,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
):
    """What exporting the session would carry: its runs and the file size.

    Raises
    ------
    HTTPException
        404 if the session does not exist.
    """
    from DashAI.back.session_package.export import (
        SessionNotFoundError,
        export_preview,
    )

    try:
        return export_preview(model_session_id, session_factory)
    except SessionNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from e


@router.post("/{model_session_id}/export")
@inject
async def export_model_session(
    model_session_id: int,
    params: SessionExportParams,
    session_factory: "sessionmaker" = Depends(lambda: di["session_factory"]),
    component_registry: "ComponentRegistry" = Depends(lambda: di["component_registry"]),
):
    """Download the session and the chosen runs as a ``.dashai`` file.

    Raises
    ------
    HTTPException
        404 if the session does not exist, 409 if the chosen runs cannot be
        exported, 500 on any other failure.
    """
    import shutil
    import tempfile
    from pathlib import Path

    from fastapi.concurrency import run_in_threadpool
    from fastapi.responses import FileResponse
    from starlette.background import BackgroundTask

    from DashAI.back.session_package.export import (
        SessionNotExportableError,
        SessionNotFoundError,
        build_session_package,
        session_filename,
    )

    workdir = Path(tempfile.mkdtemp(prefix="dashai-export-"))
    destination = workdir / "session.dashai"
    try:
        manifest = await run_in_threadpool(
            build_session_package,
            model_session_id,
            params.run_ids,
            params.include_trained_models,
            destination,
            session_factory,
            component_registry,
        )
    except SessionNotFoundError as e:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        ) from e
    except SessionNotExportableError as e:
        shutil.rmtree(workdir, ignore_errors=True)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e)) from e
    except Exception as e:
        shutil.rmtree(workdir, ignore_errors=True)
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error exporting the session",
        ) from e

    return FileResponse(
        destination,
        media_type="application/zip",
        filename=session_filename(manifest["info"]["session_name"]),
        background=BackgroundTask(shutil.rmtree, workdir, ignore_errors=True),
    )
