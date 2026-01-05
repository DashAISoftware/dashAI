"""Base Model abstract class."""

from abc import ABCMeta, abstractmethod
from typing import Any, Dict, Final, final

from kink import di

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.dependencies.database.models import Metric


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract class of all machine learning models.

    All models must extend this class
    and implement save, load, train and predict methods.
    """

    TYPE: Final[str] = "Model"
    COLOR: str = "#795548"

    @abstractmethod
    def save(self, filename: str) -> None:
        """Store an instance of a model.

        filename (Str): Indicates where to store the model,
        if filename is None, this method returns a bytes array with the model.
        """
        raise NotImplementedError

    @abstractmethod
    def load(self, filename: str) -> Any:
        """Restores an instance of a model.

        filename (Str): Indicates where the model was stored.
        """
        raise NotImplementedError

    @abstractmethod
    def train(
        self,
        x_train: DashAIDataset,
        y_train: DashAIDataset,
        x_validation: DashAIDataset = None,
        y_validation: DashAIDataset = None,
    ) -> "BaseModel":
        """Train the model with the provided data.

        Parameters
        ----------
        x_train : DashAIDataset
            The input features for training.
        y_train : DashAIDataset
            The target labels for training.
        x_validation : DashAIDataset, optional
            The input features for validation.
        y_validation : DashAIDataset, optional
            The target labels for validation.

        Returns
        -------
        BaseModel
            The trained model instance.
        """
        raise NotImplementedError

    @final
    def _save_metrics(
        self, split: SplitEnum, level: LevelEnum, results: Dict[str, float]
    ):
        """
        Save metrics to the database, appending to existing metrics
        if they exist.

        Parameters
        ----------
        split : SplitEnum
            The data split (TRAIN, VALIDATION, TEST)
        level : LevelEnum
            The metric level (LAST, TRIAL, STEP, BATCH)
        results : Dict[str, float]
            Dictionary mapping metric names to their scores
        """
        with di["session_factory"]() as db:
            # Try to find existing metric entry for this run, split, and level
            existing_metric = (
                db.query(Metric)
                .filter_by(run_id=self.run_id, split=split, level=level)
                .first()
            )

            if existing_metric:
                # Append new scores to existing lists
                for metric_name, score in results.items():
                    # If metric already exists, append or override,
                    # otherwise create new list
                    if metric_name in existing_metric.results:
                        # If last override the last value,
                        # else, append to the list
                        if level == LevelEnum.LAST:
                            existing_metric.results[metric_name][-1] = score
                        else:
                            existing_metric.results[metric_name].append(score)
                    else:
                        existing_metric.results[metric_name] = [score]

                # Mark as modified for SQLAlchemy to detect the change
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(existing_metric, "results")
            else:
                # Create new metric entry with lists
                metric_entry = Metric(
                    run_id=self.run_id,
                    split=split,
                    level=level,
                    results={name: [score] for name, score in results.items()},
                )
                db.add(metric_entry)

            db.commit()

    @final
    def calculate_metrics(
        self,
        split: SplitEnum = SplitEnum.VALIDATION,
        level: LevelEnum = LevelEnum.LAST,
        x_data: DashAIDataset = None,
        y_data: DashAIDataset = None,
    ):
        """
        Calculate and save metrics for a given data split and level.

        Parameters
        ----------
        split : SplitEnum, default=SplitEnum.VALIDATION
            The data split (TRAIN, VALIDATION, TEST).
        level : LevelEnum, default=LevelEnum.LAST
            The metric level (LAST, TRIAL, STEP, BATCH).
        x_data : DashAIDataset, optional
            The input features for the split. If None, the stored dataset
            associated with the split is used.
        y_data : DashAIDataset, optional
            The target labels for the split. If None, the stored labels
            associated with the split are used.
        """
        # Get the appropriate metrics based on split
        metrics_attr = f"{split.value}_metrics"
        metrics = getattr(self, metrics_attr, None)

        # If no metrics or run_id, skip calculation
        if not metrics or not self.run_id:
            return

        # Load data if not provided
        if x_data is None or y_data is None:
            if self.x_data is None or self.y_data is None:
                return
            x_data = self.x_data[split.value]
            y_data = self.y_data[split.value]

        # If data is empty after retrieval, skip calculation
        if x_data is None or y_data is None:
            return

        # Make predictions and transform outputs
        y_pred = self.predict(x_data)
        y_transformed = self.prepare_output(y_data, is_fit=False)

        # Calculate metric scores
        results = {}
        for metric in metrics:
            score = metric.score(y_transformed, y_pred)
            results[metric.__name__] = score

        # Save to database
        self._save_metrics(split=split, level=level, results=results)

    def prepare_dataset(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Hook for model-specific preprocessing of input features.

        Override in subclasses needing
        custom tokenization/encoding. Must not mutate input in-place.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool
            Whether the dataset is for fitting or not.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        return dataset

    def prepare_output(
        self, dataset: DashAIDataset, is_fit: bool = False
    ) -> DashAIDataset:
        """Hook for model-specific preprocessing of output targets.

        Parameters
        ----------
        dataset : DashAIDataset
            The output dataset to be transformed.
        is_fit : bool
            Whether the dataset is for fitting or not.

        Returns
        -------
        DashAIDataset
            The prepared output dataset.
        """
        return self.prepare_dataset(dataset, is_fit)
