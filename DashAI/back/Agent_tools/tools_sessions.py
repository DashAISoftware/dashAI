import json
from typing import Literal, Union

import requests
from langchain.tools import tool
from langchain_core.tools import BaseTool

from DashAI.back.Agent_tools.utils import CLASSIFICATION_METRICS
from DashAI.back.core.utils import MultilingualString
from DashAI.back.pydantic_models.runs_models import (
    MODEL_PARAMS,
    AddModelParams,
    HyperOptOptimizerParams,
    OptunaOptimizerParams,
)
from DashAI.back.pydantic_models.sessions_models import (
    CreateSessionParams,
    DeleteModelFromSessionParams,
    DeleteSession,
    GetModelSessionMetrics,
    GetSessionParameters,
    ManualDivision,
    RandomDivision,
    RunModelParams,
)


@tool(
    "get_sessions",
    description=(
        "Obtiene todas las sesiones de modelos activas del módulo 'Modelos' de DashAI."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get active model sessions", es="Obtener sesiones de modelos activas"
        )
    },
)
def get_sessions():
    """Get all active model sessions.

    Retrieves all active model sessions available in the DashAI "Modelos"
    module.

    Parameters
    ----------
    None

    Returns
    -------
    str
        Success message containing the list of active model sessions when the
        request completes successfully. Otherwise, returns an error message
        describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/model-session/"
    try:
        response = requests.get(
            endpoint,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 200:
            return f"Se ha ejecutado de forma exitosa la herramienta: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener las sesiones: {exc}"


@tool(
    "get_session_parameters",
    args_schema=GetSessionParameters,
    description=(
        "Permite obtener datos asociados a la sesión de modelo a partir del "
        "ID de la sesión.  Con esta herramienta se obtiene las columnas de salida, "
        "columnas de entrada, las métricas de evaluación consideradas en el "
        "entrenamiento, validación y prueba, los splits de los conjuntos de "
        "entrenamiento, validación y prueba, el nombre de la sesión y la fecha "
        "de creación."
    ),
    extras={
        "display_name": MultilingualString(
            en="Get model session parameters",
            es="Obtener parámetros de sesión de modelo",
        )
    },
)
def get_session_parameters(model_session_id: int):
    """Get the configuration parameters of a model session.

    Retrieves the configuration and metadata associated with a model session
    in the DashAI "Modelos" module.

    The returned information includes the input columns, output columns,
    evaluation metrics used during training, validation and testing,
    dataset split configuration, session name, and creation date.

    Parameters
    ----------
    model_session_id : int
        Identifier of the model session whose configuration and metadata
        will be retrieved.

    Returns
    -------
    str
        Success message containing the model session configuration. Otherwise,
        returns an error message describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/model-session/"
    try:
        response = requests.get(
            f"{endpoint}{model_session_id}/",
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 200:
            return f"Se ha ejecutado de forma exitosa la herramienta: {response.json()}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener la sesión: {exc}"


@tool(
    "delete_session",
    args_schema=DeleteSession,
    description=(
        "Elimina una sesión de modelo existente en el módulo 'Modelos' de DashAI."
    ),
    extras={
        "display_name": MultilingualString(
            en="Delete model session", es="Eliminar sesión de modelo"
        )
    },
)
def delete_session(model_session_id: int):
    """Delete a model session.

    Deletes an existing model session from the DashAI "Models" module.

    Parameters
    ----------
    model_session_id : int
        Identifier of the model session to delete.

    Returns
    -------
    str
        Confirmation message if the model session is successfully deleted.
        Otherwise, returns an error message describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/model-session/"
    try:
        response = requests.delete(
            f"{endpoint}{model_session_id}/",
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 204:
            return f"Sesión de modelo con ID {model_session_id} eliminada exitosamente."
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al eliminar la sesión: {exc}"


@tool(
    "get_models_execution_metrics",
    args_schema=GetModelSessionMetrics,
    description=(
        "Para cada modelo asociado a una sesión especifica del módulo "
        "'Modelos' obtiene:"
        "- ID: identificador del modelo (run_id) asociado a la sesión\n"
        "- Last_modified: fecha y hora de la última modificación del modelo\n"
        "- Delivery_time: fecha y hora de finalización del entrenamiento del modelo\n"
        "- Model_name: nombre del modelo\n"
        "- Start_time: fecha y hora de inicio del último entrenamiento del modelo\n"
        "- Parameters: hiperparámetros usados en el modelo\n"
        "- Goal_metric: métrica objetivo seleccionada para la optimización de "
        "hiperparámetros del modelo\n"
        "- End_time: fecha y hora de finalización del último entrenamiento del modelo\n"
        "- Optimizer_name: nombre del optimizador usado para la búsqueda de "
        "hiperparámetros del modelo\n"
        "- Optimizer_parameters: parámetros de configuración del optimizador usado "
        "para la búsqueda de hiperparámetros del modelo\n"
        "- Train_metrics: resultado de métricas de evaluación obtenidas en el conjunto "
        "de entrenamiento\n"
        "- Validation_metrics: resultado de métricas de evaluación obtenidas en el "
        "conjunto de validación\n"
        "- Test_metrics: resultado de métricas de evaluación obtenidas en el conjunto "
        "de prueba\n"
        "- Score: resultado de la puntuación final del modelo calculado en función a "
        "las métricas seleccionadas"
    ),
    extras={
        "display_name": MultilingualString(
            en="Get models execution metrics",
            es="Obtener métricas de ejecución de modelos",
        )
    },
)
def get_models_execution_metrics(model_session_id: int):
    """Get execution metrics for the models in a session.

    Retrieves the execution details and evaluation metrics for every model
    associated with a model session in the DashAI "Models" module.

    The returned information includes the model identifier, timestamps,
    model name, training parameters, optimization configuration, evaluation
    metrics for the training, validation, and test datasets, and the final
    score assigned to each model.

    Parameters
    ----------
    model_session_id : int
        Identifier of the model session whose associated model execution
        metrics will be retrieved.

    Returns
    -------
    str
        Success message containing the execution metrics for all models in the
        specified session. Otherwise, returns an error message describing the
        failure.
    """
    endpoint = "http://localhost:8000/api/v1/run/"
    try:
        response = requests.get(
            endpoint,
            params={
                "model_session_id": model_session_id,
                "include_scores": "true",
                "profile_id": "balanced",
            },
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 200:
            allowed_fields = {
                "id",
                "last_modified",
                "delivery_time",
                "model_name",
                "start_time",
                "parameters",
                "goal_metric",
                "end_time",
                "optimizer_name",
                "optimizer_parameters",
                "train_metrics",
                "validation_metrics",
                "test_metrics",
                "score",
            }
            result = [
                {key: value for key, value in run.items() if key in allowed_fields}
                for run in response.json()
            ]
            return f"Se ha ejecutado de forma exitosa la herramieta: \n {result}"
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al obtener las métricas de la sesión: {exc}"


@tool(
    "create_session",
    args_schema=CreateSessionParams,
    description="Crea una nueva sesión de modelo en el módulo 'Modelos' de DashAI. ",
    extras={
        "display_name": MultilingualString(
            en="Create model session", es="Crear sesión de modelo"
        )
    },
)
def create_session(
    dataset_id: int,
    task_name: str,
    name: str,
    input_columns: list[str],
    output_columns: list[str],
    splits: Union[ManualDivision, RandomDivision],
) -> str:
    """Create a new model session.

    Creates a new model session in the DashAI "Modelos" module using the
    specified dataset, task configuration, input and output columns, and
    dataset split strategy. The evaluation metrics are automatically assigned
    according to the selected task type.

    Parameters
    ----------
    dataset_id : int
        Identifier of the dataset used to create the model session.
    task_name : str
        Name of the machine learning task executed by the model session.
    name : str
        Name assigned to the model session.
    input_columns : list[str]
        Dataset columns used as input features during model training.
    output_columns : list[str]
        Dataset columns used as prediction targets.
    splits : ManualDivision | RandomDivision
        Configuration used to divide the dataset into training, validation,
        and test sets. This can be either a manual split or a random split
        with optional shuffling and stratification.

    Returns
    -------
    str
        Success message containing the information of the created model
        session. Otherwise, returns an error message describing the failure.
    """
    endpoint = "http://localhost:8000/api/v1/model-session/"

    request_params = {
        "dataset_id": dataset_id,
        "task_name": task_name,
        "name": name,
        "input_columns": input_columns,
        "output_columns": output_columns,
        "train_metrics": CLASSIFICATION_METRICS[task_name],
        "validation_metrics": CLASSIFICATION_METRICS[task_name],
        "test_metrics": CLASSIFICATION_METRICS[task_name],
        "splits": splits.model_dump_json(),
    }

    try:
        response = requests.post(
            endpoint,
            json=request_params,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 201:
            return (
                f"Se ha agregado la sesión de modelo con éxito en el módulo "
                f"modelos.  {response.json()}"
            )
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al crear la sesión: {exc}"


GOAL_METRIC = Literal[
    "Accuracy",
    "CohenKappa",
    "F1",
    "HammingDistance",
    "LogLoss",
    "Precision",
    "Recall",
    "ROCAUC",
    "ExplainedVariance",
    "MAE",
    "MedianAbsoluteError",
    "MSE",
    "R2",
    "RMSE",
    "",
]


@tool(
    "add_model_to_session",
    args_schema=AddModelParams,
    description=(
        "Agrega un nuevo modelo a una sesión de modelos existente en el módulo "
        "'Modelos' de DashAI. "
        "Usa el endpoint api/v1/run para crear la ejecución del modelo con sus "
        "hiperparámetros.  Modelos disponibles por tarea:\n"
        "TabularClassification: SVC, DecisionTreeClassifier, DummyClassifier, "
        "HistGradientBoostingClassifier, KNeighborsClassifier, LogisticRegression, "
        "RandomForestClassifier\n"
        "Regression: GradientBoostingR, MLPRegression, RandomForestRegression, "
        "RidgeRegression, LinearSVR, LinearRegression\n"
        "TextClassification: DistilBertTransformer, ModernBertTransformer, "
        "DebertaV3Transformer, BagOfWordsTextClassificationModel\n"
        "Translation: OpusMtEnESTransformer, OpusMtEsENTransformer, NllbTransformer \n"
        "Al agregar un modelo a una sesión, se puede especificar un optimizador.  "
        "Si se desea optimizar la busqueda de hiperparámetros, se debe usar "
        "OptunaOptimizer o HyperOptOptimizer y en caso de usarse, se debe "
        "especificar cuales campos del modelo se buscan optimizar junto con "
        "especificar el goal_metric  que va a ser ocupado por el optimizador "
        "para determinar cual es la mejor combinación de hiperparámetros. "
        "Los modelos de regresión pueden unicamente aceptar como optimizador "
        "OptunaOptimizer.  En tanto los modelos de clasificación tabular aceptan "
        "tanto OptunaOptimizer como HyperOptOptimizer.  \n"
        "En caso de no ocuparse un optimizador, dejar goal_metric como string vacío, "
        "optimizer_name como string vacío y optimizer_parameters como None. "
        "Al momento de escoger una goal_metric para la optimzación de campos del "
        "modelo, se debe escoger una que sea acorde a la tarea de la sesión. "
        "Para la sesiones con tarea de regresión, las goal_metrics validas son: R2, "
        "ExplainedVariance, MAE, MedianAbsoluteError, MSE, RMSE. "
        "Para las sesiones con tarea de clasificación, las goal_metrics validas son: "
        "Accuracy, CohenKappa, F1, HammingDistance, LogLoss, Precision, Recall, ROCAUC"
    ),
    extras={
        "display_name": MultilingualString(
            en="Add model to session", es="Agregar modelo a sesión"
        )
    },
)
def add_model_to_session(
    model_session_id: int,
    model_name: str,
    run_name: str,
    parameters: MODEL_PARAMS,
    optimizer_name: str,
    optimizer_parameters: Union[OptunaOptimizerParams, HyperOptOptimizerParams, None],
    goal_metric: str,
    description: str,
) -> str:
    """Add a model to an existing model session.

    Creates a new model (run) within an existing model session in the DashAI
    "Models" module. The model is configured with the specified
    hyperparameters and can optionally include a hyperparameter optimization
    strategy. When an optimizer is enabled, the corresponding optimizer
    parameters and optimization goal metric must also be provided.

    Parameters
    ----------
    model_session_id : int
        Identifier of the model session to which the model will be added.
    model_name : str
        Name of the model class to create. The selected model determines the
        required structure of the ``parameters`` argument.
    run_name : str
        Unique name assigned to the model within the session.
    parameters : MODEL_PARAMS
        Hyperparameter configuration for the selected model. The expected
        structure depends on the value of ``model_name``.
    optimizer_name : str
        Name of the hyperparameter optimizer to use. Supported values are
        ``"OptunaOptimizer"``, ``"HyperOptOptimizer"``, or an empty string
        when no optimizer is required.
    optimizer_parameters : OptunaOptimizerParams | HyperOptOptimizerParams | None
        Configuration of the selected hyperparameter optimizer. This value
        should be ``None`` when no optimizer is used.
    goal_metric : str
        Evaluation metric used by the optimizer to determine the best
        hyperparameter configuration. This value must be compatible with the
        task associated with the model session. Use an empty string when no
        optimizer is specified.
    description : str
        Optional description associated with the model.

    Returns
    -------
    str
        Confirmation message if the model is successfully added to the
        specified session. Otherwise, returns an error message describing the
        failure.
    """
    endpoint = "http://localhost:8000/api/v1/run/"

    request_params = {
        "model_session_id": model_session_id,
        "model_name": model_name,
        "name": run_name,
        "parameters": parameters.model_dump(),
        "optimizer_name": optimizer_name,
        "plot_history_path": "",
        "plot_slice_path": "",
        "plot_contour_path": "",
        "plot_importance_path": "",
        "goal_metric": goal_metric,
        "description": description,
    }

    if optimizer_parameters is not None:
        request_params["optimizer_parameters"] = optimizer_parameters.model_dump()
    else:
        request_params["optimizer_parameters"] = {}

    try:
        response = requests.post(
            endpoint,
            json=request_params,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 201:
            return "Se ha agregado el nuevo modelo a la sesión especificada."
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al agregar el modelo a la sesión: {exc}"


@tool(
    "delete_model_from_session",
    args_schema=DeleteModelFromSessionParams,
    description=(
        "Elimina un modelo existente dentro de una sesión del módulo 'Modelos' de "
        "DashAI. El identificador requerido es el run_id del modelo, no el "
        "model_session_id."
    ),
    extras={
        "display_name": MultilingualString(
            en="Delete model from session", es="Eliminar modelo de sesión"
        )
    },
)
def delete_model_from_session(run_id: int) -> str:
    """Delete a model from a session.

    Deletes an existing model (run) from a model session in the DashAI
    "Models" module.

    Parameters
    ----------
    run_id : int
        Identifier of the model (run) to delete. This identifier corresponds
        to the model execution and not to the model session.

    Returns
    -------
    str
        Confirmation message if the model is successfully deleted. Otherwise,
        returns an error message describing the failure.
    """
    endpoint = f"http://localhost:8000/api/v1/run/{run_id}"

    try:
        response = requests.delete(
            endpoint,
            headers={"Content-Type": "application/json", "Accept-Language": "es"},
        )
        if response.status_code == 204:
            return f"Modelo con run_id {run_id} eliminado exitosamente de la sesión."
        return f"Error {response.status_code}: {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: No se puede conectar al servidor"
    except requests.exceptions.RequestException as exc:
        return f"Error al eliminar el modelo de la sesión: {exc}"


@tool(
    "run_model",
    args_schema=RunModelParams,
    description=(
        "Ejecuta el entrenamiento, validación y testeo de un modelo que ya existe "
        "dentro de una sesión del módulo 'Modelos' de DashAI. Elimina operaciones "
        "previas asociadas al run cuando existan, resetea los resultados del modelo "
        "y luego encola el trabajo de entrenamiento."
    ),
    extras={"display_name": MultilingualString(en="Run model", es="Ejecutar modelo")},
)
def run_model(run_id: int):
    """Run a model training job.

    Resets the execution state of an existing model (run), removes any
    previous execution results, and enqueues a new training job in the
    DashAI "Modelos" module. The execution includes the training,
    validation, and testing stages.

    Parameters
    ----------
    run_id : int
        Identifier of the model (run) to execute. This identifier corresponds
        to the model execution and not to the model session.

    Returns
    -------
    str
        Success message containing the identifier of the queued training job.
        Otherwise, returns an error message describing the failure.
    """

    reset_endpoint = f"http://localhost:8000/api/v1/run/{run_id}/reset"
    job_endpoint = "http://localhost:8000/api/v1/job/"
    try:
        reset_response = requests.patch(
            reset_endpoint, headers={"Accept-Language": "es"}
        )
        if reset_response.status_code != 200:
            return (
                "Error al resetear el modelo antes del entrenamiento: "
                f"{reset_response.status_code}: {reset_response.text}"
            )
        response = requests.post(
            job_endpoint,
            files={
                "job_type": (None, "ModelJob"),
                "kwargs": (None, json.dumps({"run_id": run_id})),
            },
            headers={"Accept-Language": "es"},
        )
        if response.status_code == 201:
            job = response.json()
            return (
                f"Entrenamiento del modelo '{run_id}' iniciado correctamente.  "
                f"El id del job es: {job}"
            )
        return (
            f"Error al encolar el entrenamiento: "
            f"{response.status_code}: {response.text}"
        )
    except requests.exceptions.ConnectionError as exc:
        return f"Error: No se puede conectar al servidor {exc}"
    except requests.exceptions.RequestException as exc:
        return f"Error al iniciar el entrenamiento: {exc}"


SESSIONS_TOOLS: list[BaseTool] = [
    get_sessions,
    create_session,
    delete_session,
    get_session_parameters,
    get_models_execution_metrics,
    add_model_to_session,
    delete_model_from_session,
    run_model,
]
