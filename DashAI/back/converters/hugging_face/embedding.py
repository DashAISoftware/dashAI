import torch
from datasets import Dataset, concatenate_datasets
from transformers import AutoModel, AutoTokenizer

from DashAI.back.converters.hugging_face_wrapper import HuggingFaceWrapper
from DashAI.back.core.schema_fields import (
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset


class EmbeddingSchema(BaseSchema):
    model_name: schema_field(
        enum_field(
            [
                # Sentence Transformers Models
                "sentence-transformers/all-MiniLM-L6-v2",
                "sentence-transformers/all-mpnet-base-v2",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                "sentence-transformers/all-distilroberta-v1",
                # BERT Models
                "bert-base-uncased",
                "bert-large-uncased",
                "bert-base-multilingual-cased",
                "distilbert-base-uncased",
                # RoBERTa Models
                "roberta-base",
                "roberta-large",
                "distilroberta-base",
            ]
        ),
        "sentence-transformers/all-MiniLM-L6-v2",
        "Name of the pre-trained model to use",
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

    pooling_strategy: schema_field(
        enum_field(["mean", "cls", "max"]),
        "mean",
        "Strategy to pool token embeddings into sentence embedding",
    )  # type: ignore


class Embedding(HuggingFaceWrapper):
    """HuggingFace embedding converter."""

    SCHEMA = EmbeddingSchema
    DESCRIPTION = "Convert text to embeddings using HuggingFace transformer models."

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.pooling_strategy = kwargs.get("pooling_strategy", "mean")
        self.model_name = kwargs.get(
            "model_name", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.device = kwargs.get("device", "cpu")
        self.max_length = kwargs.get("max_length", 512)
        self.batch_size = kwargs.get("batch_size", 32)
        self.model = None
        self.tokenizer = None

    def _load_model(self):
        """Load the embedding model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()

    def _process_batch(self, batch: DashAIDataset) -> DashAIDataset:
        """Process a batch of text into embeddings."""
        all_column_embeddings = []

        for column in batch.column_names:
            # Get text data from dataset
            texts = [row[column] for row in batch]

            # Tokenize
            encoded = self.tokenizer(
                texts,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )

            # Move to device
            encoded = {k: v.to(self.device) for k, v in encoded.items()}

            # Get embeddings
            with torch.no_grad():
                outputs = self.model(**encoded)
                hidden_states = outputs.last_hidden_state

                # Apply pooling strategy
                if self.pooling_strategy == "mean":
                    embeddings = torch.mean(hidden_states, dim=1)
                elif self.pooling_strategy == "cls":
                    embeddings = hidden_states[:, 0]
                else:  # max pooling
                    embeddings = torch.max(hidden_states, dim=1)[0]

            embeddings_np = embeddings.cpu().numpy()

            # Create a dictionary with embedding columns
            embedding_dict = {
                f"{column}_embedding_{i}": embeddings_np[:, i].tolist()
                for i in range(embeddings_np.shape[1])
            }

            # Create a HuggingFace Dataset and convert it to a PyArrow table
            hf_dataset = Dataset.from_dict(embedding_dict)
            arrow_table = hf_dataset.data.table

            # Create a new dataset for this column's embeddings
            column_dataset = DashAIDataset(arrow_table)
            all_column_embeddings.append(column_dataset)

        # Concatenate all column embeddings
        concatenated_dataset = concatenate_datasets(all_column_embeddings)
        return DashAIDataset(concatenated_dataset.data.table)
