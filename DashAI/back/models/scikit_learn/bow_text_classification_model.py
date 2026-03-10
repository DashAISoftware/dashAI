from pathlib import Path
from typing import Optional, Union

import joblib
import numpy as np
import pyarrow as pa
from datasets import Dataset
from sklearn.feature_extraction.text import CountVectorizer

from DashAI.back.core.schema_fields import (
    BaseSchema,
    component_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import (
    DashAIDataset,
    to_dashai_dataset,
)
from DashAI.back.models.text_classification_model import TextClassificationModel
from DashAI.back.types.categorical import Categorical
from DashAI.back.types.value_types import Float


class BagOfWordsTextClassificationModelSchema(BaseSchema):
    """
    NumericalWrapperForText is a metamodel that allows text classification using
    tabular classifiers and a tokenizer.
    """

    tabular_classifier: schema_field(
        component_field(parent="TabularClassificationModel"),
        placeholder={"component": "SVC", "params": {}},
        description=MultilingualString(
            en=(
                "Tabular model used as the underlying model "
                "to generate the text classifier."
            ),
            es=(
                "Modelo tabular usado como el modelo subyacente "
                "para generar el clasificador de texto."
            ),
        ),
        alias=MultilingualString(en="Tabular classifier", es="Clasificador tabular"),
    )  # type: ignore
    ngram_min_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en=(
                "The lower boundary of the range of n-values for different word "
                "n-grams or char n-grams to be extracted. It must be an integer "
                "greater or equal than 1"
            ),
            es=(
                "El límite inferior del rango de valores n para diferentes n-gramas "
                "de palabras o caracteres a extraer. Debe ser un entero mayor o "
                "igual a 1"
            ),
        ),
        alias=MultilingualString(en="Ngram min N", es="Ngrama mínimo N"),
    )  # type: ignore
    ngram_max_n: schema_field(
        int_field(ge=1),
        placeholder=1,
        description=MultilingualString(
            en=(
                "The upper boundary of the range of n-values for different word "
                "n-grams or char n-grams to be extracted. It must be an integer "
                "greater or equal than 1"
            ),
            es=(
                "El límite superior del rango de valores n para diferentes n-gramas "
                "de palabras o caracteres a extraer. Debe ser un entero mayor o "
                "igual a 1"
            ),
        ),
        alias=MultilingualString(en="Ngram max N", es="Ngrama máximo N"),
    )  # type: ignore


class BagOfWordsTextClassificationModel(TextClassificationModel):
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

    DISPLAY_NAME: str = MultilingualString(
        en="Bag of Words Text Classifier",
        es="Clasificador de Texto Bolsa de Palabras",
    )
    DESCRIPTION: str = MultilingualString(
        en="Text classification using bag-of-words features and tabular classifiers.",
        es=(
            "Clasificación de texto usando bolsa de palabras y "
            "clasificadores tabulares."
        ),
    )
    COLOR: str = "#FF5722"
    ICON: str = "TextFields"
    SCHEMA = BagOfWordsTextClassificationModelSchema

    def __init__(self, **kwargs) -> None:
        """
        Initialize the BagOfWordsTextClassificationModel.

        Parameters
        ----------
        kwargs : dict
            A dictionary containing the parameters for the model, including:
            - tabular_classifier:
            The tabular classification model from DashAI to be used.
            - ngram_min_n: Minimum n-gram value.
            - ngram_max_n: Maximum n-gram value.
        """

        self.classifier = kwargs["tabular_classifier"]
        self.vectorizer = CountVectorizer(
            ngram_range=(kwargs["ngram_min_n"], kwargs["ngram_max_n"])
        )

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

    def train(
        self,
        x: Dataset,
        y: Dataset,
        x_validation: Dataset = None,
        y_validation: Dataset = None,
    ):
        input_column = x.column_names[0]
        self.vectorizer.fit(x[input_column])
        tokenizer_func = self.get_vectorizer(input_column)
        tokenized_dataset = x.map(tokenizer_func, remove_columns=x.column_names)
        tokenized_dataset = to_dashai_dataset(tokenized_dataset)

        self.classifier.train(tokenized_dataset, y)

    def predict(self, x: Dataset):
        input_column = x.column_names[0]

        tokenizer_func = self.get_vectorizer(input_column)
        tokenized_dataset = x.map(tokenizer_func, remove_columns=x.column_names)
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

    def prepare_dataset(self, dataset: DashAIDataset, is_fit=False):
        """Apply the model transformations to the dataset.

        Parameters
        ----------
        dataset : DashAIDataset
            The dataset to be transformed.
        is_fit : bool, optional
            If True, the method will apply transformations needed for fitting the model.

        Returns
        -------
        DashAIDataset
            The prepared dataset ready to be converted to
            an accepted format in the model.
        """
        try:
            input_column = dataset.column_names[0]
            input_type = dataset.types[input_column]

            if isinstance(input_type, Categorical):
                if is_fit:
                    dataset = super().prepare_dataset(dataset, is_fit=True)
                    return dataset
                else:
                    dataset = super().prepare_dataset(dataset, is_fit=False)
                    return dataset

            if is_fit:
                self.vectorizer.fit(dataset[input_column])

            tokenizer_func = self.get_vectorizer(input_column)
            dataset = dataset.map(tokenizer_func, remove_columns=input_column)
            dataset = to_dashai_dataset(dataset)

            dataset.types = {
                col: Float(arrow_type=pa.float32())
                for col in dataset.column_names
                if col.startswith(input_column)
            }

            return dataset
        except Exception as e:
            print(f"Couldn't apply transformations to the dataset for the model: {e}")

    def prepare_output(self, dataset, is_fit=False):
        return self.classifier.prepare_output(dataset, is_fit)
