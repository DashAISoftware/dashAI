# ruff: noqa
import json
import time
from datetime import datetime
from pathlib import Path

from fastapi.encoders import jsonable_encoder
from langchain_core.messages import AIMessage

from DashAI.back.Agent_tools.tools_datasets import upload_dataset
from DashAI.back.Agent_tools.tools_sessions import add_model_to_session, create_session
from DashAI.back.pydantic_models.datasets_models import CSVUploadParams
from DashAI.back.pydantic_models.sessions_models import RandomDivision

DATASET_FILE_PATH = r"C:\Users\FANB\Undecimo semestre\Datasets\iris.csv"
TRANSLATION_DATASET_FILE_PATH = (
    r"C:\Users\FANB\Undecimo semestre\Datasets\data_translation_mini.csv"
)
REGRESSION_DATASET_FILE_PATH = (
    r"C:\Users\FANB\Undecimo semestre\Datasets\train_regression.csv"
)
TEXT_CLASSIFICATION_DATASET_FILE_PATH = r"C:\Users\FANB\Undecimo semestre\Datasets\Corona_NLP_test_text_classification_mini.csv"


def _upload_dataset_from_path(file_path: str, name: str) -> str:
    return upload_dataset.invoke(
        {
            "file_path": file_path,
            "name": name,
            "inference_rows": 1000,
            "extra_params": CSVUploadParams(
                dataloader="CSVDataLoader",
                separator=",",
                header="infer",
                names=None,
                encoding="utf-8",
                na_values=None,
                keep_default_na=True,
                true_values=None,
                false_values=None,
                skip_blank_lines=True,
                skiprows=None,
                nrows=None,
            ),
        }
    )


def upload_iris_dataset(name: str) -> str:
    return _upload_dataset_from_path(DATASET_FILE_PATH, name)


def upload_translation_mini_dataset(name: str) -> str:
    return _upload_dataset_from_path(TRANSLATION_DATASET_FILE_PATH, name)


def upload_regression_dataset(name: str) -> str:
    return _upload_dataset_from_path(REGRESSION_DATASET_FILE_PATH, name)


def upload_text_classification_dataset(name: str) -> str:
    return _upload_dataset_from_path(TEXT_CLASSIFICATION_DATASET_FILE_PATH, name)


def load_iris_dataset(dataset_name: str):
    upload_iris_dataset(dataset_name)


def create_model_session(
    upload_dataset_fn: object,
    dataset_name: str,
    task_name: str,
    input_columns: list[str],
    output_columns: list[str],
):
    upload_dataset_fn(dataset_name)
    create_session.invoke(
        {
            "dataset_id": 1,
            "task_name": task_name,
            "name": f"{dataset_name}_session",
            "input_columns": input_columns,
            "output_columns": output_columns,
            "splits": RandomDivision(
                train=0.6,
                validation=0.2,
                test=0.2,
                shuffle=True,
                stratify=True,
                seed=42,
                splitType="random",
            ),
        }
    )


def create_model_session_with_dataset(
    dataset_name: str,
    task_name: str,
    input_columns: list[str],
    output_columns: list[str],
):
    create_model_session(
        upload_iris_dataset,
        dataset_name,
        task_name,
        input_columns,
        output_columns,
    )


def create_session_with_model(
    upload_dataset_fn,
    dataset_name: str,
    task_name: str,
    input_columns: list[str],
    output_columns: list[str],
    model_name: str,
    run_name: str,
    parameters: dict,
    optimizer_name: str = "",
    optimizer_parameters: dict | None = None,
    goal_metric: str = "",
    description: str = "",
):
    create_model_session(
        upload_dataset_fn,
        dataset_name,
        task_name,
        input_columns,
        output_columns,
    )
    add_model_to_session.invoke(
        {
            "model_session_id": 1,
            "model_name": model_name,
            "run_name": run_name,
            "parameters": parameters,
            "optimizer_name": optimizer_name,
            "optimizer_parameters": optimizer_parameters,
            "goal_metric": goal_metric,
            "description": description,
        }
    )


def save_evaluation_results(
    test_name,
    result_tool_calling,
    result_tool_args,
    result_llm,
    duration_seconds,
    message_count,
    total_tokens,
    results_file_name,
    model_name,
):
    file_path = Path(__file__).resolve().parent / results_file_name
    existing = {}
    if file_path.exists():
        try:
            existing = json.loads(file_path.read_text(encoding="utf-8"))
        except ValueError:
            existing = {}

    model_key = model_name
    if existing and all(
        isinstance(value, dict) and "timestamp" in value for value in existing.values()
    ):
        existing = {model_key: existing}

    if model_key not in existing or not isinstance(existing[model_key], dict):
        existing[model_key] = {}

    entry = {
        "duration_seconds": duration_seconds,
        "message_count": message_count,
        "total_tokens": total_tokens,
        "result_tool_calling_evaluator": jsonable_encoder(result_tool_calling),
        "result_tool_args_evaluator": jsonable_encoder(result_tool_args),
        "result_llm_evaluator": jsonable_encoder(result_llm),
        "timestamp": datetime.now().isoformat(),
    }
    existing[model_key][test_name] = entry
    file_path.write_text(
        json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def get_total_tokens(messages: list) -> int:
    total_tokens = 0
    for message in messages:
        if isinstance(message, AIMessage):
            token_usage = message.response_metadata.get("token_usage", {})
            total_tokens += int(token_usage.get("total_tokens", 0))
    return total_tokens


def run_agent_case(
    agent,
    llm_judge,
    tool_calling_evaluator,
    tool_args_evaluator,
    test_name: str,
    user_input: str,
    reference_outputs,
    results_file_name,
):
    start_time = time.perf_counter()
    output = agent.generate_answer_test(user_input)
    end_time = time.perf_counter()

    text_output = output["messages"][-1].content
    result_tool_calling_evaluator = tool_calling_evaluator(
        outputs=output, reference_outputs=reference_outputs
    )
    result_tool_args_evaluator = tool_args_evaluator(
        outputs=output, reference_outputs=reference_outputs
    )
    result_llm_evaluator = llm_judge(inputs=user_input, outputs=text_output)

    save_evaluation_results(
        test_name,
        result_tool_calling_evaluator,
        result_tool_args_evaluator,
        result_llm_evaluator,
        end_time - start_time,
        len(output["messages"]),
        total_tokens=get_total_tokens(output.get("messages", [])),
        results_file_name=results_file_name,
        model_name=agent.model_name,
    )
    return {
        "assert_evaluation_llm_as_a_judge": result_llm_evaluator,
        "assert_evaluation_tools_calling": result_tool_calling_evaluator,
        "assert_evaluation_tools_calling_with_args": result_tool_args_evaluator,
    }


def assert_evaluations_agent(results: dict):
    if results["assert_evaluation_llm_as_a_judge"] is not None:
        assert_evaluation_llm_as_a_judge(results["assert_evaluation_llm_as_a_judge"])
    if results["assert_evaluation_tools_calling"] is not None:
        assert_evaluation_tools_calling(results["assert_evaluation_tools_calling"])
    # if results["assert_evaluation_tools_calling_with_args"] is not None:
    #     assert_evaluation_tools_calling_with_args(results["assert_evaluation_tools_calling_with_args"])


def assert_evaluation_llm_as_a_judge(result):
    result = result.model_dump()

    assert result["request_fulfillment_text"] == 1
    assert result["response_structure"] == 1
    assert result["clarity_response"] > 0.6
    assert result["enthusiasm_response"] > 0.6
    assert result["logical_coherence"] > 0.6


def assert_evaluation_tools_calling(result):
    assert result["score"] == True


def assert_evaluation_tools_calling_with_args(result):
    assert result["score"] == True
