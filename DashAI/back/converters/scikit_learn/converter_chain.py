from DashAI.back.converters.base_converter import BaseConverter
from DashAI.back.converters.scikit_learn.sklearn_like_converter import (
    SklearnLikeConverter,
)


class ConverterChain(BaseConverter, SklearnLikeConverter):
    """Chain of converters."""

    DESCRIPTION = (
        "A ConverterChain applies a sequence of converters to preprocess "
        "data, passing the output of one converter to the next, with "
        "its scope defined by the first converter."
    )

    def __init__(self, steps):
        self.steps = steps

    def fit(self, x, y=None):
        for step in self.steps:
            step.fit(x, y)
        return self

    def transform(self, x, y=None):
        for step in self.steps:
            x = step.transform(x, y)
        return x
