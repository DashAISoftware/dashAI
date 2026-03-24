from typing import TYPE_CHECKING

from DashAI.back.models.scikit_learn.sklearn_like_model import SklearnLikeModel

if TYPE_CHECKING:
    from numpy import ndarray

    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class SklearnLikeClassifier(SklearnLikeModel):
    """Class for handling sklearn-like classifier models."""

    def predict(self, x_pred: "DashAIDataset") -> "ndarray":
        """Make a prediction with the model

        Parameters
        ----------
        x_pred : DashAIDataset
            Dataset with the input data columns.

        Returns
        -------
        np.ndarray
            Array with the predicted target values for x_pred
        """
        import pandas as pd

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        if isinstance(x_pred, DashAIDataset):
            try:
                x_prepared = self.prepare_dataset(x_pred, is_fit=False)
            except ValueError:
                x_prepared = x_pred
            x_pred = x_prepared.to_pandas()
        elif isinstance(x_pred, pd.DataFrame):
            pass

        return super().predict_proba(x_pred)
