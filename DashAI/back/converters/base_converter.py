from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Final, Type, Union

from DashAI.back.config_object import ConfigObject
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class BaseConverterSchema(BaseSchema):
    """
    Base schema for converters, it defines the parameters to be used in each converter.

    The schema should be assigned to the converter class to define the parameters of
    its configuration.
    """


class BaseConverter(ConfigObject, ABC):
    """
    Base class for all converters

    Converters are for modifying the data in a supervised or unsupervised way
    (e.g. by adding, changing, or removing columns, but not by adding or removing rows)
    """

    TYPE: Final[str] = "Converter"
    DISPLAY_NAME: Final[str] = ""
    DESCRIPTION: Final[str] = ""
    SHORT_DESCRIPTION: Final[str] = ""
    IMAGE_PREVIEW: Final[str] = ""
    CATEGORY: Final[str] = "Other"
    COLOR: Final[str] = "rgb(255, 255, 255)"
    SUPERVISED: bool = False
    SCHEMA: BaseConverterSchema

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get metadata values for the current converter.

        Returns
        -------
        Dict[str, Any]
            Dictionary with the metadata
        """
        meta: Dict[str, Any] = dict(getattr(cls, "metadata", {}) or {})
        meta["display_name"] = cls.DISPLAY_NAME if cls.DISPLAY_NAME else cls.__name__
        meta["short_description"] = (
            cls.SHORT_DESCRIPTION if cls.SHORT_DESCRIPTION else ""
        )
        meta["image_preview"] = cls.IMAGE_PREVIEW if cls.IMAGE_PREVIEW else ""
        meta["category"] = cls.CATEGORY if cls.CATEGORY else "Other"
        meta["color"] = cls.COLOR if cls.COLOR else "rgb(255, 255, 255)"
        meta["supervised"] = cls.SUPERVISED

        return meta

    def changes_row_count(self) -> bool:
        """
        Indicates if the converter changes the number of rows in the dataset.
        Samplers typically do, while most other transformers do not.
        """
        return False

    @abstractmethod
    def fit(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> Type[BaseConverter]:
        """Fit the converter.
        This method should allow to validate the converter's parameters.

        Parameters
        ----------
        X : DashAIDataset
            Training data
        y: DashAIDataset
            Target data for supervised learning

        Returns
        ----------
        self
            The fitted converter object.
        """
        raise NotImplementedError

    @abstractmethod
    def transform(
        self, x: DashAIDataset, y: Union[DashAIDataset, None] = None
    ) -> DashAIDataset:
        """Transform the dataset.

        Parameters
        ----------
        X : DashAIDataset
            Dataset to be converted
        y: DashAIDataset
            Target vectors

        Returns
        -------
            Dataset converted
        """
        raise NotImplementedError
