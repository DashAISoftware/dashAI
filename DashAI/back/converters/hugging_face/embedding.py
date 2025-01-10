import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModel
from DashAI.back.converters.hugging_face_wrapper import HuggingFaceWrapper
from DashAI.back.core.schema_fields import (
    string_field,
    int_field,
    enum_field,
    schema_field,
    none_type,
)
from DashAI.back.core.schema_fields.base_schema import BaseSchema


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
        "cuda",
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
        # self.pooling_strategy = kwargs.get(
        #     "pooling_strategy", self.SCHEMA.pooling_strategy.default
        # )
        self.pooling_strategy = "mean"
        print("Pooling strategy:", self.pooling_strategy)
        self.model = None
        self.tokenizer = None

    def _load_model(self):
        """Load the embedding model and tokenizer."""
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()

    def _process_batch(self, batch: pd.DataFrame) -> pd.DataFrame:
        """Process a batch of text into embeddings."""
        all_column_embeddings = []

        for column in batch.columns:
            texts = batch[column].tolist()

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
            column_df = pd.DataFrame(
                embeddings_np,
                columns=[
                    f"{column}_embedding_{i}" for i in range(embeddings_np.shape[1])
                ],
            )
            all_column_embeddings.append(column_df)

        # Concatenate embeddings from all columns
        return pd.concat(all_column_embeddings, axis=1)
