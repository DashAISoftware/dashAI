from abc import abstractmethod
from typing import Final

from beartype.typing import Dict, List, Tuple, Union

from DashAI.back.converters.scikit_learn.label_encoder import LabelEncoder


class BaseSplitter:
    TYPE: Final[str] = "Splitter"

    def __init__(self, splits_data):
        self.random_state = splits_data.get("random_state", 42)
        self.shuffle = splits_data.get("shuffle", True)

    @abstractmethod
    # el split devuelve una tupla con x e y DashaiDatasets o una lista de ellos
    def split(
        self, x, y
    ) -> Tuple[Union[object, List[object]], Union[object, List[object]], Dict]:
        raise NotImplementedError("The split method must be implemented by subclasses.")

    def prepare_y(self, y):
        if all(isinstance(v, int) for v in y):
            return y

        try:
            return LabelEncoder().fit_transform(y)
        except Exception as e:
            raise ValueError("Cannot encode labels") from e
