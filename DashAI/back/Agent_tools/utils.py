import json
import time

import requests

from DashAI.back.pydantic_models.converters_models import (
    ConverterColumn,
)
from DashAI.back.pydantic_models.datasets_models import ExplorerColumn

_EXPLORER_FINISHED = 3
_EXPLORER_ERROR = 4


CLASSIFICATION_METRICS = {
    "TabularClassificationTask": [
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
        "CohenKappa",
        "HammingDistance",
        "LogLoss",
        "ROCAUC",
    ],
    "TextClassificationTask": [
        "Accuracy",
        "Precision",
        "Recall",
        "F1",
        "CohenKappa",
        "HammingDistance",
        "LogLoss",
        "ROCAUC",
    ],
    "TranslationTask": ["Bleu", "Chrf", "Ter"],
    "RegressionTask": [
        "MSE",
        "RMSE",
        "MAE",
        "R2",
        "MedianAbsoluteError",
        "ExplainedVariance",
    ],
}


def check_explorer_status(explorer_id: int):
    endpoint = f"http://localhost:8000/api/v1/explorer/{explorer_id}/"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return response.json()
        else:
            return (
                f"Error al consultar el estado del explorer: "
                f"{response.status_code} - {response.text}"
            )
    except requests.exceptions.RequestException as e:
        return f"Error de conexión al consultar el estado del explorer: {e}"


def create_explorer_and_enqueue(
    exploration_type: str,
    notebook_id: int,
    columns: list[ExplorerColumn],
    parameters: dict,
):
    endpoint = "http://localhost:8000/api/v1/explorer"
    data = {
        "notebook_id": notebook_id,
        "columns": [column.model_dump() for column in columns],
        "exploration_type": exploration_type,
        "parameters": parameters,
        "name": None,
    }
    response = requests.post(
        endpoint, json=data, headers={"Content-Type": "application/json"}
    )
    if response.status_code not in (200, 201):
        return (
            f"Error al crear {exploration_type}: {response.status_code}-{response.text}"
        )
    created = response.json()
    explorer_id = created.get("id")

    url_job = "http://localhost:8000/api/v1/job/"
    kwargs_json = json.dumps({"explorer_id": explorer_id})
    job_data = {
        "job_type": (None, "ExplorerJob"),
        "stop_when_queue_empties": (None, "true"),
        "kwargs": (None, kwargs_json),
    }
    job_response = requests.post(url_job, files=job_data)
    if job_response.status_code not in (200, 201):
        return (
            f"Explorador creado (id={explorer_id}) pero falló el "
            f"encolamiento: {job_response.status_code}-{job_response.text}"
        )
    requests.post("http://localhost:8000/api/v1/job/start/")

    for _attempt in range(7):
        time.sleep(5)
        try:
            explorer_data = check_explorer_status(explorer_id)
            if isinstance(explorer_data, dict):
                status_code = explorer_data.get("status")
                if status_code == _EXPLORER_FINISHED:
                    return {
                        "explorer": explorer_data,
                        "job": job_response.json(),
                        "message": f"{exploration_type} creado y ejecutado "
                        f"exitosamente.",
                    }
                if status_code == _EXPLORER_ERROR:
                    return (
                        f"El explorador '{exploration_type}' (id={explorer_id}) "
                        f"terminó con error."
                    )
        except Exception:
            pass

    return {
        "explorer": created,
        "job": job_response.json(),
        "message": (
            f"{exploration_type} encolado exitosamente (id={explorer_id}), pero han "
            f"transcurrido 35 segundos desde el encolamiento y el proceso aún está en "
            f"curso. El proceso continúa ejecutándose en segundo plano."
        ),
    }


_CONVERTER_FINISHED = 3
_CONVERTER_ERROR = 4


def check_converter_status(converter_id: int):
    endpoint = f"http://localhost:8000/api/v1/converter/{converter_id}"
    try:
        response = requests.get(endpoint, headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return response.json()
        return (
            f"Error al consultar el estado del converter: "
            f"{response.status_code} - {response.text}"
        )

    except requests.exceptions.RequestException as e:
        return f"Error de conexión al consultar el estado del converter: {e}"


def create_converter_and_enqueue(
    converter_type: str,
    notebook_id: int,
    columns: list[ConverterColumn],
    params: dict,
    order: int,
    target: ConverterColumn | None = None,
):
    endpoint = "http://localhost:8000/api/v1/converter/"
    scope = {
        "columns": [
            {
                "idx": col.idx + 1,
                "columnName": col.columnName,
                "valueType": col.valueType,
                "dataType": col.dataType,
            }
            for col in columns
        ],
        "rows": [],
    }
    if target is not None and isinstance(target, ConverterColumn):
        target = {
            "idx": target.idx + 1,
            "columnName": target.columnName,
            "valueType": target.valueType,
            "dataType": target.dataType,
        }
    payload = {
        "notebook_id": notebook_id,
        "converter": converter_type,
        "parameters": {
            "order": order,
            "params": params,
            "scope": scope,
            "target": target if target else None,
        },
    }
    try:
        response = requests.post(
            endpoint, json=payload, headers={"Content-Type": "application/json"}
        )
        if response.status_code != 201:
            return (
                f"Error al crear el converter '{converter_type}': "
                f"{response.status_code} - {response.text}"
            )
        converter_id = response.json()["id"]
    except requests.exceptions.RequestException as e:
        return f"Error de conexión al crear el converter: {e}"

    url_job = "http://localhost:8000/api/v1/job/"
    kwargs_json = json.dumps({"converter_id": converter_id})
    job_data = {
        "job_type": (None, "ConverterJob"),
        "stop_when_queue_empties": (None, "true"),
        "kwargs": (None, kwargs_json),
    }
    try:
        job_response = requests.post(url_job, files=job_data)
        if job_response.status_code not in (200, 201):
            return (
                f"Converter creado (id={converter_id}) pero falló el encolamiento: "
                f"{job_response.status_code} - {job_response.text}"
            )
    except requests.exceptions.RequestException as e:
        return f"Converter creado (id={converter_id}) pero error al encolar: {e}"

    requests.post("http://localhost:8000/api/v1/job/start/")

    for _ in range(7):
        time.sleep(5)
        try:
            converter_data = check_converter_status(converter_id)
            if isinstance(converter_data, dict):
                status_code = converter_data.get("status")
                if status_code == _CONVERTER_FINISHED:
                    return {
                        "converter": converter_data,
                        "job": job_response.json(),
                        "message": f"{converter_type} creado y aplicado exitosamente.",
                    }
                if status_code == _CONVERTER_ERROR:
                    return (
                        f"El converter '{converter_type}' (id={converter_id}) "
                        f"terminó con error."
                    )

        except Exception:
            pass

    return {
        "converter": {"id": converter_id},
        "job": job_response.json(),
        "message": (
            f"{converter_type} encolado exitosamente (id={converter_id}), pero han "
            f"transcurrido 35 segundos desde el encolamiento y el proceso aún está en "
            f"curso. El proceso continúa ejecutándose en segundo plano."
        ),
    }
