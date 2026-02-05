"""HuggingFace embedding converter with lazy-loaded dependencies."""

from DashAI.back.converters.category.advanced_preprocessing import (
    AdvancedPreprocessingConverter,
)
from DashAI.back.converters.hugging_face_wrapper import HuggingFaceWrapper
from DashAI.back.core.schema_fields import enum_field, int_field, schema_field
from DashAI.back.core.schema_fields.base_schema import BaseSchema
from DashAI.back.core.utils import MultilingualString
from DashAI.back.dataloaders.classes.dashai_dataset import DashAIDataset
from DashAI.back.types.dashai_data_type import DashAIDataType
from DashAI.back.types.value_types import Float


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
        description=MultilingualString(
            en="Name of the pre-trained model to use",
            es="Nombre del modelo preentrenado a usar",
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

    pooling_strategy: schema_field(
        enum_field(["mean", "cls", "max"]),
        "mean",
        description=MultilingualString(
            en="Strategy to pool token embeddings into sentence embedding",
            es="Estrategia para agrupar embeddings de tokens en uno de oración",
        ),
    )  # type: ignore


class Embedding(AdvancedPreprocessingConverter, HuggingFaceWrapper):
    """HuggingFace embedding converter."""

    SCHEMA = EmbeddingSchema
    DESCRIPTION = MultilingualString(
        en="Convert text to embeddings using HuggingFace transformer models.",
        es="Convierte texto a embeddings usando modelos de HuggingFace.",
    )
    DISPLAY_NAME = MultilingualString(en="Embedding", es="Embedding")
    IMAGE_PREVIEW = "embedding.png"

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

    def get_output_type(self, column_name: str = None) -> DashAIDataType:
        """Returns Float32 as the output type for embeddings."""
        import pyarrow as pa

        return Float(arrow_type=pa.float32())

    def _load_model(self):
        """Load the embedding model and tokenizer."""
        from transformers import AutoModel, AutoTokenizer

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModel.from_pretrained(self.model_name).to(self.device)
        self.model.eval()

    def _process_batch(self, batch: DashAIDataset) -> DashAIDataset:
        """Process a batch of text into embeddings."""
        import torch
        from datasets import Dataset, concatenate_datasets

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
