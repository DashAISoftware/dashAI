from pathlib import Path
from typing import Optional, Union

import joblib
import numpy as np
from datasets import Dataset
from sklearn.feature_extraction.text import CountVectorizer

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    schema_field,
)
from DashAI.back.dataloaders.classes.dashai_dataset import to_dashai_dataset
from DashAI.back.models.scikit_learn.sklearn_like_model import SklearnLikeModel
from DashAI.back.models.text_classification_model import TextClassificationModel


class BagOfWordsTextClassificationModelSchema(BaseSchema):
    """
    NumericalWrapperForText is a metamodel that allows text classification using
    tabular classifiers and a tokenizer.
    """

    tabular_classifier: schema_field(
        component_field(parent="TabularClassificationModel"),
        placeholder={"component": "SVC", "params": {}},
        description=(
            "Tabular model used as the underlying model "
            "to generate the text classifier."
        ),
    )  # type: ignore
    ngram_min_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=(
            "The lower boundary of the range of n-values for different word n-grams "
            "or char n-grams to be extracted. It must be an integer greater or equal "
            "than 1"
        ),
    )  # type: ignore
    ngram_max_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=(
            "The upper boundary of the range of n-values for different word n-grams "
            "or char n-grams to be extracted. It must be an integer greater or equal "
            "than 1"
        ),
    )  # type: ignore


class BagOfWordsTextClassificationModel(TextClassificationModel, SklearnLikeModel):
    """Text classification meta-model.

    The metamodel has two main components:

    - Tabular classification model: the underlying model that processes the data and
        provides the prediction.
    - Vectorizer: a BagOfWords that vectorizes the text into a sparse matrix to give
        the correct input to the underlying model.

    The tabular_model and vectorizer are created in the __init__ method and stored in
    the model.

    To train the tabular_model the vectorizer is fitted and used to transform the
    train dataset.

    To predict with the tabular_model the vectorizer is used to transform the dataset.
    """

    SCHEMA = BagOfWordsTextClassificationModelSchema

    def __init__(self, **kwargs) -> None:
        """
        Initialize the BagOfWordsTextClassificationModel.

        Parameters
        ----------
        kwargs : dict
            A dictionary containing the parameters for the model, including:
            - tabular_classifier: Configuration for the underlying classifier.
            - ngram_min_n: Minimum n-gram value.
            - ngram_max_n: Maximum n-gram value.
        """
        transformed_kwargs = self._transform_parameters(kwargs)
        self.SCHEMA.model_validate(transformed_kwargs)
        params = transformed_kwargs["tabular_classifier"]["params"]
        self.fixed_params, self.optimizable_params = self._extract_parameters(params)
        transformed_kwargs["tabular_classifier"]["params"] = self.fixed_params
        validated_kwargs = self.validate_and_transform(transformed_kwargs)

        self.classifier = validated_kwargs["tabular_classifier"]
        self.vectorizer = CountVectorizer(
            ngram_range=(kwargs["ngram_min_n"], kwargs["ngram_max_n"])
        )

    def _transform_parameters(self, kwargs: dict) -> dict:
        """
        Transform the raw parameters from the frontend into a format compatible
        with the model.

        Parameters
        ----------
        kwargs : dict
            Raw parameters from the frontend.

        Returns
        -------
        dict
            Transformed parameters.
        """
        transformed_dict = kwargs.copy()
        if "tabular_classifier" in transformed_dict:
            tabular_classifier = transformed_dict["tabular_classifier"]
            if "properties" in tabular_classifier:
                sub_model = tabular_classifier["properties"]["params"]["comp"]
                transformed_dict["tabular_classifier"] = {
                    "component": sub_model.get("component"),
                    "params": sub_model.get("params", {}),
                }
        return transformed_dict

    def _extract_parameters(self, parameters: dict) -> dict:
        """
        Extract fixed and optimizable parameters from a dictionary.

        This method processes a dictionary of parameters and separates them into
        fixed parameters and optimizable parameters. Fixed parameters are those
        that are not intended to be optimized, while optimizable parameters are
        those that have bounds defined for optimization.

        Parameters
        ----------
        parameters : dict
            A dictionary containing parameter names as keys and parameter
            specifications as values.

        Returns
        -------
        tuple
            A tuple containing two dictionaries:
            - fixed_params: A dictionary of parameters that are fixed and not
            intended to be optimized.
            - optimizable_params: A dictionary of parameters that are intended to
            be optimized, with their respective lower and upper bounds.
        """
        fixed_params = {
            key: (
                param["fixed_value"]
                if isinstance(param, dict) and "optimize" in param
                else param
            )
            for key, param in parameters.items()
        }
        optimizable_params = {
            key: (param["lower_bound"], param["upper_bound"])
            for key, param in parameters.items()
            if isinstance(param, dict) and param.get("optimize") is True
        }
        return fixed_params, optimizable_params

    def get_vectorizer(self, input_column: str, output_column: Optional[str] = None):
        """Factory that returns a function to transform a text classification dataset
        into a tabular classification dataset.

        To do this, the column "text" is vectorized (using a BagOfWords) into a sparse
        matrix of size NxM, where N is the number of examples and M is the vocabulary
        size.

        Each column of the output matrix will be named using the input_column name as
        prefix and the column number as suffix.

        The output_column is not changed.

        Parameters
        ----------
        input_column : str
            name the input column of the dataset. This column will be vectorized.

        output_column : str
            name the output column of the dataset.

        Returns
        -------
        Function
            Function for vectorize the dataset.
        """

        def _vectorize(example) -> dict:
            vectorized_sentence = self.vectorizer.transform(
                [example[input_column]]
            ).toarray()
            output_example = {}
            for idx in range(np.shape(vectorized_sentence)[1]):
                output_example[input_column + str(idx)] = vectorized_sentence[0][idx]
            return output_example

        return _vectorize

    def fit(self, x: Dataset, y: Dataset):
        input_column = x.column_names[0]
        self.vectorizer.fit(x[input_column])
        tokenizer_func = self.get_vectorizer(input_column)
        tokenized_dataset = x.map(tokenizer_func, remove_columns="text")
        tokenized_dataset = to_dashai_dataset(tokenized_dataset)

        self.classifier.fit(tokenized_dataset, y)

    def predict(self, x: Dataset):
        input_column = x.column_names[0]

        tokenizer_func = self.get_vectorizer(input_column)
        tokenized_dataset = x.map(tokenizer_func, remove_columns="text")
        tokenized_dataset = to_dashai_dataset(tokenized_dataset)

        return self.classifier.predict(tokenized_dataset)

    def save(self, filename: Union[str, Path]) -> None:
        """Save the model in the specified path."""
        joblib.dump(self, filename)

    @staticmethod
    def load(filename: Union[str, Path]) -> None:
        """Load the model of the specified path."""
        model = joblib.load(filename)
        return model
