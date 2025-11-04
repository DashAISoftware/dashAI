from datasets import Dataset, concatenate_datasets
from transformers import AutoTokenizer

from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.converters.hugging_face_wrapper import HuggingFaceWrapper
from DashAI.back.core.schema_fields import enum_field, int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class TokenizerSchema(BaseSchema):
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
        "Name of the pre-trained tokenizer model",
    )  # type: ignore

    max_length: schema_field(
        int_field(ge=1), 512, "Maximum sequence length for tokenization"
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1), 32, "Number of samples to process at once"
    )  # type: ignore

    device: schema_field(
        enum_field(["cuda", "cpu"]),
        "cpu",
        "Device to use for computation",
    )  # type: ignore


class TokenizerConverter(AdvancedPreprocessingConverter, HuggingFaceWrapper):
    """Converter that tokenizes text and stores each token ID in a separate column."""

    SCHEMA = TokenizerSchema
    DESCRIPTION = (
        "Tokenize text into input IDs; each token ID goes into its own column. "
        "Attention mask is ignored."
    )
    DISPLAY_NAME = "Tokenizer"
    IMAGE_PREVIEW = "tokenizer.png"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.model_name = kwargs.get("model_name", "bert-base-uncased")
        self.device = kwargs.get("device", "cpu")
        self.max_length = kwargs.get("max_length", 512)
        self.batch_size = kwargs.get("batch_size", 32)
        self.tokenizer = None

    def _load_model(self):
        """Load tokenizer only."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

    def _process_batch(self, batch: DashAIDataset) -> DashAIDataset:
        """
        Tokenize a batch of text columns and store each input_id in a separate column.
        """
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
