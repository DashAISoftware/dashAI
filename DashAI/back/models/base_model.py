"""Base Model abstract class."""

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Final, final

from kink import di

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.enums.metrics import LevelEnum, SplitEnum
from DashAI.back.dependencies.database.models import Metric

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseModel(ConfigObject, metaclass=ABCMeta):
    """Abstract class of all machine learning models.

    All models must extend this class
    and implement save, load, train and predict methods.
    """

    TYPE: Final[str] = "Model"
    DISPLAY_NAME: str = ""
    DESCRIPTION: str = ""
    COLOR: str = "#795548"
    ICON: str = "Science"

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """Get metadata values for the current model.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata including icon.
        """
        metadata: Dict[str, Any] = {}
        metadata["icon"] = cls.ICON if cls.ICON else "Science"

        return metadata

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
        x_train: "DashAIDataset",
        y_train: "DashAIDataset",
        x_validation: "DashAIDataset" = None,
        y_validation: "DashAIDataset" = None,
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
        self,
        split: SplitEnum,
        level: LevelEnum,
        results: Dict[str, float],
        log_index: int = None,
    ):
        with di["session_factory"]() as db:
            # Initialize tracking dict if not exists
            if not hasattr(self, "_metric_step_counters"):
                self._metric_step_counters = {}

            # Create a unique key for this run/split/level combination
            counter_key = (self.run_id, split, level)

            # 1. Determine log_index
            if counter_key not in self._metric_step_counters:
                steps = (
                    db.query(Metric.step)
                    .filter_by(run_id=self.run_id, split=split, level=level)
                    .order_by(Metric.step.desc())
                    .limit(2)
                    .all()
                )

                if not steps:
                    current, previous = 0, 0
                elif len(steps) == 1:
                    current, previous = steps[0][0], 0
                else:
                    current, previous = steps[0][0], steps[1][0]

                self._metric_step_counters[counter_key] = {
                    "current": current,
                    "previous": previous,
                }

            counter = self._metric_step_counters[counter_key]

            current_max = counter["current"]
            previous_max = counter["previous"]

            # Compute delta (preserve spacing)
            delta = current_max - previous_max
            if delta <= 0:
                delta = 1

            # Case 1: no log_index -> advance naturally
            if log_index is None or log_index <= current_max:
                log_index = current_max + delta

            # Update the in-memory tracker
            counter["previous"] = current_max
            counter["current"] = log_index

            # 2. Handle 'LAST' level replacement logic
            if level == LevelEnum.LAST:
                for name, value in results.items():
                    existing = (
                        db.query(Metric)
                        .filter_by(
                            run_id=self.run_id, split=split, level=level, name=name
                        )
                        .first()
                    )

                    if existing:
                        existing.value = value
                        existing.step = log_index
                    else:
                        db.add(
                            Metric(
                                run_id=self.run_id,
                                split=split,
                                level=level,
                                name=name,
                                value=value,
                                step=log_index,
                            )
                        )

            # 3. Standard logging (STEP, BATCH, TRIAL) - just insert
            else:
                metric_entries = [
                    Metric(
                        run_id=self.run_id,
                        split=split,
                        level=level,
                        name=name,
                        value=score,
                        step=log_index,
                    )
                    for name, score in results.items()
                ]
                db.add_all(metric_entries)

            db.commit()

    @final
    def calculate_metrics(
        self,
        split: SplitEnum = SplitEnum.VALIDATION,
        level: LevelEnum = LevelEnum.LAST,
        log_index: int = None,
        x_data: "DashAIDataset" = None,
        y_data: "DashAIDataset" = None,
    ):
        """
        Calculate and save metrics for a given data split and level.

        Parameters
        ----------
        split : SplitEnum, default=SplitEnum.VALIDATION
            The data split (TRAIN, VALIDATION, TEST).
        level : LevelEnum, default=LevelEnum.LAST
            The metric level (LAST, TRIAL, STEP, BATCH).
        log_index : int, optional
            The index for logging purposes. If None, it will save the metric
            as last index + 1.
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
        self._save_metrics(
            split=split, level=level, results=results, log_index=log_index
        )

    def prepare_dataset(
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
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
        self, dataset: "DashAIDataset", is_fit: bool = False
    ) -> "DashAIDataset":
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
