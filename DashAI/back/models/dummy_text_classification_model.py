from typing import Any

from datasets import Dataset

from DashAI.back.models.text_classification_model import TextClassificationModel


class DummyTextClassifier(TextClassificationModel):
    """Dummy model for text classification.

    Implements a simple classifier that predicts the majority class
    of a binary classification problem.
    """

    def __init__(self, strategy: str = "most_frequent"):
        """
        Parameters
        ----------
        strategy : str, optional
            Strategy for predictions:
            - 'most_frequent': Always predicts the most common class in the dataset.
        """
        super().__init__()
        self.strategy = strategy
        self.most_frequent_label = None
        self.is_trained = False

    def tokenize_data(self, dataset: Dataset) -> Dataset:
        """Tokenize data."""
        return dataset

    def fit(self, x_train: Dataset, y_train: Dataset) -> None:
        """Fit the dummy model."""
        if self.strategy == "most_frequent":
            column_name = y_train.column_names[0]
            labels = y_train[column_name]
            self.most_frequent_label = max(set(labels), key=labels.count)
        self.is_trained = True

    def predict(self, x_pred: Dataset) -> Dataset:
        """Predict labels for the input dataset."""
        if not self.is_trained:
            raise RuntimeError("The model must be trained before making predictions.")

        if self.strategy == "most_frequent":
            predictions = [self.most_frequent_label] * len(x_pred)
        else:
            raise ValueError(f"Unknown strategy: {self.strategy}")

        return Dataset.from_dict({"predictions": predictions})

    def save(self, filename: str) -> None:
        with open(filename, "w") as f:
            f.write(f"{self.strategy}\n")
            f.write(f"{self.most_frequent_label}\n")

    def load(self, filename: str) -> Any:
        with open(filename, "r") as f:
            self.strategy = f.readline().strip()
            self.most_frequent_label = f.readline().strip()
        self.is_trained = True
