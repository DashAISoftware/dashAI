class RetrieverError(Exception):
    """Base exception for all retriever-related errors."""


class MissingParameterError(RetrieverError):
    """A required parameter was not provided to the retriever."""

    def __init__(self, param_name: str, retriever_name: str):
        super().__init__(
            f"Missing required parameter '{param_name}' "
            f"in retriever '{retriever_name}'."
        )
        self.param_name = param_name
        self.retriever_name = retriever_name


class ExtraKwargsMissingError(RetrieverError):
    """One or more required infrastructure kwargs are missing."""

    def __init__(self, missing_keys: set, retriever_name: str):
        super().__init__(
            f"Missing required extra kwargs {missing_keys} "
            f"in retriever '{retriever_name}'."
        )
        self.missing_keys = missing_keys
        self.retriever_name = retriever_name


class CompositeValidationError(RetrieverError):
    """A composite retriever has an invalid configuration."""


class UnitRetrieverChildError(RetrieverError):
    """A composite retriever received a child that is not a UnitRetriever."""

    def __init__(self, child_class: str, strategy: str):
        super().__init__(
            f"Cascade strategy '{strategy}' requires UnitRetriever children, "
            f"but child '{child_class}' is a composite."
        )
        self.child_class = child_class
        self.strategy = strategy
