"""Infrastructure mixin for FAISS-backed DashAI models.

This mixin is not tied to any specific task type (clustering, regression, etc.).
Any future DashAI model backed by a FAISS index — regardless of task — can
inherit from this class to get float32 conversion, save/load, and pickle support
for FAISS indexes at no extra cost.
"""

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class FaissBaseModel:
    """Mixin providing FAISS infrastructure for DashAI models.

    Handles the three concerns shared by every FAISS-backed model:

    1. **Data conversion** — DashAIDataset → contiguous float32 numpy array,
       which is the only format FAISS accepts.
    2. **Persistence** — ``save`` / ``load`` via joblib, with a custom pickle
       protocol so FAISS index objects (which are not natively picklable) are
       serialised as raw bytes using ``faiss.serialize_index``.
    3. **Extensibility** — any future model type (classification, regression,
       retrieval) can reuse this mixin without coupling to the clustering
       contract.
    """

    def _to_float32(self, x_dataset: "DashAIDataset") -> np.ndarray:
        """Convert a DashAIDataset to a contiguous float32 numpy array.

        Only numeric columns are retained. FAISS requires a C-contiguous
        float32 matrix; ``np.ascontiguousarray`` guarantees that even after
        column selection.

        Parameters
        ----------
        x_dataset : DashAIDataset
            Input dataset to convert.

        Returns
        -------
        numpy.ndarray of shape (n_samples, n_features), dtype float32

        Raises
        ------
        ValueError
            If no numeric columns are present in the dataset.
        """
        x_pandas = x_dataset.to_pandas()
        numeric = x_pandas.select_dtypes(include=["number"])
        if numeric.empty:
            raise ValueError(
                f"{self.__class__.__name__} requires at least one numeric feature."
            )
        return np.ascontiguousarray(numeric.values, dtype=np.float32)

    def save(self, filename: str) -> None:
        """Save the fitted model to disk using joblib.

        The custom ``__getstate__`` protocol serialises any FAISS index
        stored in ``self._index`` before joblib pickles the object.

        Parameters
        ----------
        filename : str
            Destination path for the serialised model.
        """
        import joblib

        joblib.dump(self, filename)

    def load(self, filename: str) -> Any:
        """Restore a fitted model from disk.

        Parameters
        ----------
        filename : str
            Path to a previously saved model file.

        Returns
        -------
        Any
            The deserialised model instance.
        """
        import joblib

        return joblib.load(filename)

    def __getstate__(self) -> dict:
        """Serialise the FAISS index as raw bytes before pickling."""
        state = self.__dict__.copy()
        if state.get("_index") is not None:
            import faiss

            state["_index"] = faiss.serialize_index(state["_index"]).tobytes()
            state["_index_serialized"] = True
        return state

    def __setstate__(self, state: dict) -> None:
        """Restore the FAISS index from raw bytes after unpickling."""
        if state.pop("_index_serialized", False):
            import faiss

            index_bytes = np.frombuffer(state["_index"], dtype=np.uint8)
            state["_index"] = faiss.deserialize_index(index_bytes)
        self.__dict__.update(state)
