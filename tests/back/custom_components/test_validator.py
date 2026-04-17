from DashAI.back.custom_components.validator import validate_source

COMPLETE_MODEL_SOURCE = """
from DashAI.back.models.base_model import BaseModel


class MyCustomModel(BaseModel):
    DISPLAY_NAME = "My Custom Model"

    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def train(self, x_train, y_train, x_validation=None, y_validation=None):
        return self

    def predict(self, x_data):
        return []
"""


MISSING_METHOD_SOURCE = """
from DashAI.back.models.base_model import BaseModel


class IncompleteModel(BaseModel):
    def save(self, filename):
        pass

    def load(self, filename):
        return self

    def predict(self, x_data):
        return []
"""


WRONG_BASE_SOURCE = """
class Wrong:
    pass
"""


def test_valid_source_passes():
    result = validate_source(
        source=COMPLETE_MODEL_SOURCE,
        class_name="MyCustomModel",
        base_class_name="BaseModel",
    )
    assert result.ok is True
    assert result.cls.__name__ == "MyCustomModel"


def test_missing_abstract_method_fails():
    result = validate_source(
        source=MISSING_METHOD_SOURCE,
        class_name="IncompleteModel",
        base_class_name="BaseModel",
    )
    assert result.ok is False
    assert any("train" in e for e in result.errors)


def test_wrong_base_class_fails():
    result = validate_source(
        source=WRONG_BASE_SOURCE,
        class_name="Wrong",
        base_class_name="BaseModel",
    )
    assert result.ok is False


def test_class_name_mismatch_fails():
    result = validate_source(
        source=COMPLETE_MODEL_SOURCE,
        class_name="Mismatch",
        base_class_name="BaseModel",
    )
    assert result.ok is False


def test_syntax_error_fails():
    result = validate_source(
        source="class Broken(:\n    pass",
        class_name="Broken",
        base_class_name="BaseModel",
    )
    assert result.ok is False
    assert any("SyntaxError" in e for e in result.errors)
