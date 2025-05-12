from abc import ABCMeta

from sklearn.base import BaseEstimator, TransformerMixin


class SklearnLikeConverter(BaseEstimator, TransformerMixin, metaclass=ABCMeta):
    """Abstract class of a sklearn transformer."""
