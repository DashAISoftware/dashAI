"""Helper to move an explainer's data into the model's feature space.

Explainers receive the model input as the task prepared it, exactly as
``predict`` receives it in the prediction job: raw columns, before any model
specific preprocessing. That is what explainers that perturb the input and
query ``model.predict`` need, since ``predict`` applies the model preparation
itself.

Explainers that instead build feature matrices (``to_pandas``) and hand them
to a third party library (SHAP, DiCE, scikit-learn inspection) must work in
the model's own feature space, because those libraries call the model with
plain frames that bypass the model preparation. Such explainers call
:func:`prepare_model_input` on both the background data and the instances so
that both live in the same space.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


def prepare_model_input(model: Any, dataset: "DashAIDataset") -> "DashAIDataset":
    """Apply the model's own input preprocessing to a dataset.

    Parameters
    ----------
    model : Any
        The DashAI model being explained.
    dataset : DashAIDataset
        Input features as the task prepared them.

    Returns
    -------
    DashAIDataset
        The dataset in the model's feature space, or the dataset unchanged
        when the model does not define ``prepare_dataset``.
    """
    prepare = getattr(model, "prepare_dataset", None)
    if prepare is None:
        return dataset
    return prepare(dataset, is_fit=False)
