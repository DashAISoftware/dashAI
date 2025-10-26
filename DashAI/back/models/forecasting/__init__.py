"""Forecasting models for time series prediction."""

from .base_forecasting_model import ForecastingModel
from .prophet_model import ProphetModel

__all__ = [
    "ForecastingModel",
    "ProphetModel",
]
