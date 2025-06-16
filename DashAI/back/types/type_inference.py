from abc import ABC, abstractmethod


class InferenceSystem(ABC):
    """
    A class to represent an inference system for type checking.
    This class is a placeholder and can be extended with actual inference logic.
    """

    def __init__(self):
        pass

    def infer_type(self, value):
        """
        Infer the type of the given value.
        
        :param value: The value whose type is to be inferred.
        :return: The inferred type of the value.
        """
        return type(value).__name__  # Returns the name of the type of the value.