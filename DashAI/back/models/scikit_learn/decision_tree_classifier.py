from sklearn.tree import DecisionTreeClassifier as _DecisionTreeClassifier

from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    float_field,
    none_type,
    optimizer_int_field,
    schema_field,
    union_type,
)
from DashAI.back.models.scikit_learn.sklearn_like_classifier import (
    SklearnLikeClassifier,
)
from DashAI.back.models.tabular_classification_model import TabularClassificationModel


class DecisionTreeClassifierSchema(BaseSchema):
    """Decision Trees are a set of are a non-parametric supervised learning method that
    learns simple decision rules (structured as a tree) inferred from the data features.
    """

    criterion: schema_field(
        enum_field(enum=["entropy", "gini", "log_loss"]),
        placeholder="entropy",
        description="The function to measure the quality of a split. Supported "
        "criteria are “gini” for the Gini impurity and “log_loss” and “entropy” both "
        "for the Shannon information gain.",
    )  # type: ignore
    max_depth: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 10,
        },
        description="The maximum depth of the tree. If None, then nodes are "
        "expanded until all leaves are pure or until all leaves contain less than "
        "min_samples_split samples.",
    )  # type: ignore
    min_samples_split: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 5,
        },
        description="The minimum number of samples required to split an internal node.",
    )  # type: ignore
    min_samples_leaf: schema_field(
        optimizer_int_field(ge=1),
        placeholder={
            "optimize": False,
            "fixed_value": 1,
            "lower_bound": 1,
            "upper_bound": 5,
        },
        description="The minimum number of samples required to be at a leaf node.",
    )  # type: ignore
    max_features: schema_field(
        none_type(
            union_type(enum_field(enum=["sqrt", "log2"]), float_field(gt=0.0, le=1.0))
        ),
        placeholder=None,
        description="The number of features to consider when looking for the best "
        "split. If float, then max_features is a percentage of "
        "the total number of features.",
    )  # type: ignore


class DecisionTreeClassifier(
    TabularClassificationModel, SklearnLikeClassifier, _DecisionTreeClassifier
):
    """Scikit-learn's Decision Tree Classifier wrapper for DashAI."""

    SCHEMA = DecisionTreeClassifierSchema
    DISPLAY_NAME: str = "Decision Tree"
    COLOR: str = "#4CAF50"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
