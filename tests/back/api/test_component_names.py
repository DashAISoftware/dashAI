"""What the built-in registry holds, checked over the whole of it.

The registry stores a component under its class name and resolves
compatibility by exact name. Two consequences no single component's test can
see:

- a second class with the same name replaces the first in silence
  (``ComponentRegistry.register_component``), so names have to be unique;
- a relationship to a name nobody registers is kept and never queried, so a
  component naming the forecasting family would offer itself to nothing.

Lives under ``tests/back/api`` to reuse the ``client`` fixture.
"""

from collections import Counter

from DashAI.back.initial_components import get_initial_components


def test_every_built_in_component_has_its_own_name():
    names = Counter(component.__name__ for component in get_initial_components())

    assert [name for name, count in names.items() if count > 1] == []


def test_the_forecasting_family_is_never_registered():
    names = {component.__name__ for component in get_initial_components()}

    assert "ForecastingTask" not in names
    assert "SingleSeriesForecastingTask" in names


def test_no_registered_component_names_the_forecasting_family(client):
    registry = client.app.container["component_registry"]

    naming_it = [
        component["name"]
        for component in registry.get_components_by_types()
        if "ForecastingTask" in getattr(component["class"], "COMPATIBLE_COMPONENTS", [])
    ]

    assert naming_it == []


def test_the_concrete_task_is_offered_its_models_and_strategies(client):
    registry = client.app.container["component_registry"]

    related = {
        component["name"]
        for component in registry.get_related_components("SingleSeriesForecastingTask")
    }

    assert {
        "NaiveForecaster",
        "SeasonalNaiveForecaster",
        "ARIMA",
        "ExponentialSmoothing",
        "ForecastingHoldoutEvaluationStrategy",
        "ForecastingCrossValidationEvaluationStrategy",
        "TemporalHoldoutSplitter",
        "RollingOriginSplitter",
        "MAE",
        "RMSE",
        "OptunaOptimizer",
    } <= related
