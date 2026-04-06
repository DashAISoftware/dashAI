from typing import TYPE_CHECKING

from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.converters.hugging_face_wrapper import HuggingFaceWrapper
from DashAI.back.core.schema_fields import enum_field, int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString

if TYPE_CHECKING:
    from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TokenizerSchema(BaseSchema):
    """Schema for TokenizerConverter hyperparameters."""

    model_name: schema_field(
        enum_field(
            [
                "bert-base-uncased",
                "bert-large-uncased",
                "distilbert-base-uncased",
                "roberta-base",
                "roberta-large",
                "distilroberta-base",
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
            ]
        ),
        "bert-base-uncased",
        description=MultilingualString(
            en="Name of the pre-trained tokenizer model",
            es="Nombre del modelo de tokenización preentrenado",
        ),
    )  # type: ignore

    max_length: schema_field(
        int_field(ge=1),
        512,
        description=MultilingualString(
            en="Maximum sequence length for tokenization",
            es="Longitud máxima de secuencia para la tokenización",
        ),
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        32,
        description=MultilingualString(
            en="Number of samples to process at once",
            es="Número de muestras a procesar a la vez",
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(["cuda", "cpu"]),
        "cpu",
        description=MultilingualString(
            en="Device to use for computation",
            es="Dispositivo a usar para el cómputo",
        ),
    )  # type: ignore


class TokenizerConverter(AdvancedPreprocessingConverter, HuggingFaceWrapper):
    """Converter that tokenizes text and stores each token ID in a separate column."""

    SCHEMA = TokenizerSchema
    DESCRIPTION = MultilingualString(
        en=(
            "Tokenize text into input IDs; each token ID goes into its own column. "
            "Attention mask is ignored."
        ),
        es=(
            "Tokeniza texto a IDs de entrada; cada ID va en su propia columna. "
            "Se ignora la máscara de atención."
        ),
    )
    DISPLAY_NAME = MultilingualString(en="Tokenizer", es="Tokenizador")
    IMAGE_PREVIEW = "tokenizer.png"

    def __init__(self, **kwargs):
        """Initialise the tokenizer converter and extract schema parameters.

        Parameters
        ----------
        **kwargs : dict
            model_name : str, optional
                HuggingFace tokenizer model ID.
                Default ``"bert-base-uncased"``.
            device : str, optional
                Torch device string. Default ``"cpu"``.
            max_length : int, optional
                Maximum token sequence length. Default ``512``.
            batch_size : int, optional
                Number of examples per inference batch. Default ``32``.
        """
        super().__init__(**kwargs)
        self.model_name = kwargs.get("model_name", "bert-base-uncased")
        self.device = kwargs.get("device", "cpu")
        self.max_length = kwargs.get("max_length", 512)
        self.batch_size = kwargs.get("batch_size", 32)
        self.tokenizer = None

    def _load_model(self):
        """Load tokenizer only."""
        from transformers import AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def _process_batch(self, batch: "DashAIDataset") -> "DashAIDataset":
        """Tokenise a batch of text columns and store token IDs as integer columns.

        Each text column is tokenised with the loaded HuggingFace tokenizer.
        The resulting token-id sequence for each column is stored as a new
        ``Integer``-typed column whose name matches the source column.

        Parameters
        ----------
        batch : DashAIDataset
            A slice of the full dataset. Each column must contain string values.

        Returns
        -------
        DashAIDataset
            Dataset where each original text column is replaced by its
            token-ID list column.
        """
        from datasets import Dataset, concatenate_datasets

        from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset

        all_column_tokens = []

        for column in batch.column_names:
            texts = [row[column] for row in batch]

            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

            # Move tensor to the specified device
            input_ids = encoded["input_ids"].to(self.device)

            # Create a dictionary with each token in its own column
            column_dict = {
                f"{column}_token_{i}": input_ids[:, i].tolist()
                for i in range(input_ids.size(1))
            }

            hf_dataset = Dataset.from_dict(column_dict)
            column_dataset = DashAIDataset(hf_dataset.data.table)
            all_column_tokens.append(column_dataset)

        # Concatenate all tokenized columns
        concatenated_dataset = concatenate_datasets(all_column_tokens)
        return DashAIDataset(concatenated_dataset.data.table)
