"""The atomic units are exposed as regular registry components."""

import pytest
from fastapi.testclient import TestClient

EXPECTED_UNITS = {
    "LoadDatasetUnit",
    "PrepareAndSplitUnit",
    "BuildModelUnit",
    "FitModelUnit",
    "EvaluateModelUnit",
    "SaveModelUnit",
    "ApplyConverterUnit",
    "FitConverterUnit",
    "TransformDatasetUnit",
    "SaveDatasetUnit",
    "RunExplorationUnit",
    "SaveExplorationUnit",
    "LoadTrainedModelUnit",
    "LoadTrainingDatasetUnit",
    "BuildManualInputUnit",
    "PredictUnit",
    "SavePredictionUnit",
    "LoadRunModelUnit",
    "BuildGlobalExplainerUnit",
    "BuildLocalExplainerUnit",
    "PrepareExplanationDataUnit",
    "GenerateGlobalExplanationUnit",
    "GenerateLocalExplanationUnit",
}


@pytest.fixture(name="units", scope="module")
def get_units(client: TestClient):
    response = client.get("/api/v1/component/?select_types=Unit")
    assert response.status_code == 200, response.text
    return {component["name"]: component for component in response.json()}


def test_every_unit_is_registered(units):
    assert set(units) == EXPECTED_UNITS


def test_units_are_registered_under_the_unit_type(units):
    for unit in units.values():
        assert unit["type"] == "Unit"


def test_units_expose_a_schema_the_front_can_render(units):
    for name, unit in units.items():
        assert unit["configurable_object"] is True, name
        assert "properties" in unit["schema"], name


def test_unit_schemas_describe_their_configuration(units):
    assert set(units["LoadDatasetUnit"]["schema"]["properties"]) == {
        "dataset_id",
        "notebook_id",
    }
    assert set(units["PrepareAndSplitUnit"]["schema"]["properties"]) == {
        "task_name",
        "input_columns",
        "output_columns",
        "splits",
    }
    assert "model" in units["BuildModelUnit"]["schema"]["properties"]
    assert "optimizer" in units["FitModelUnit"]["schema"]["properties"]
    assert set(units["ApplyConverterUnit"]["schema"]["properties"]) == {
        "converter",
        "scope",
        "target",
    }
    assert set(units["FitConverterUnit"]["schema"]["properties"]) == {
        "converter",
        "scope",
        "target",
    }
    # No converter to pick: it arrives already fitted through the context.
    assert set(units["TransformDatasetUnit"]["schema"]["properties"]) == {
        "scope",
        "target",
    }
    # SaveDatasetUnit is configuration-free: it saves where the load said.
    assert units["SaveDatasetUnit"]["schema"]["properties"] == {}
    assert set(units["RunExplorationUnit"]["schema"]["properties"]) == {
        "explorer_id",
        "explorer",
    }
    # SaveExplorationUnit only picks the destination; how the result is
    # serialised belongs to the explorer that produced it.
    assert set(units["SaveExplorationUnit"]["schema"]["properties"]) == {"explorer_id"}
    assert set(units["LoadTrainedModelUnit"]["schema"]["properties"]) == {"run_id"}
    assert set(units["PredictUnit"]["schema"]["properties"]) == {
        "task_name",
        "input_columns",
        "output_columns",
    }
    assert set(units["SavePredictionUnit"]["schema"]["properties"]) == {
        "input_columns",
        "output_columns",
    }
    assert set(units["BuildGlobalExplainerUnit"]["schema"]["properties"]) == {
        "explainer"
    }
    assert set(units["BuildLocalExplainerUnit"]["schema"]["properties"]) == {
        "explainer"
    }
    assert set(units["GenerateGlobalExplanationUnit"]["schema"]["properties"]) == {
        "explainer_id"
    }


def test_component_fields_tell_the_front_which_components_to_offer(units):
    """The recursive part of the schema system.

    A component field does not inline the chosen component's schema; it
    carries a ``parent`` hint so the front can list the candidates and then
    fetch that component's own schema to render the nested form.
    """
    model = units["BuildModelUnit"]["schema"]["properties"]["model"]
    optimizer = units["FitModelUnit"]["schema"]["properties"]["optimizer"]
    converter = units["ApplyConverterUnit"]["schema"]["properties"]["converter"]
    explorer = units["RunExplorationUnit"]["schema"]["properties"]["explorer"]

    assert model["parent"] == "BaseModel"
    assert optimizer["parent"] == "BaseOptimizer"
    assert converter["parent"] == "BaseConverter"
    assert explorer["parent"] == "BaseExplorer"

    # Global and local explainers are separate registries with separate base
    # classes, and a component field carries a single parent hint. Hence two
    # sibling units with one required field each: making a single field cover
    # both scopes would need it to be optional, and an optional component field
    # is emitted as an anyOf, which hides the hint from the front — that is what
    # the assertions below would catch.
    global_explainer = units["BuildGlobalExplainerUnit"]["schema"]["properties"]
    local_explainer = units["BuildLocalExplainerUnit"]["schema"]["properties"]
    assert global_explainer["explainer"]["parent"] == "BaseGlobalExplainer"
    assert local_explainer["explainer"]["parent"] == "BaseLocalExplainer"
    assert set(model["properties"]) == {"component", "params"}
    assert set(converter["properties"]) == {"component", "params"}


def test_a_component_field_parent_resolves_to_real_components(client: TestClient):
    response = client.get("/api/v1/component/?component_parent=BaseOptimizer")
    assert response.status_code == 200, response.text

    names = {component["name"] for component in response.json()}
    assert "OptunaOptimizer" in names


def test_units_do_not_leak_into_the_job_listing(client: TestClient):
    response = client.get("/api/v1/component/?select_types=Job")
    assert response.status_code == 200, response.text

    job_names = {component["name"] for component in response.json()}
    assert not (job_names & EXPECTED_UNITS)
    assert "ModelJob" in job_names
