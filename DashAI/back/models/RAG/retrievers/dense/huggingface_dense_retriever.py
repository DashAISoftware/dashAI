from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
    HuggingFaceEmbedding,
)
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import DenseRetriever

METRICS = ["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]

HF_MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "sentence-transformers/all-mpnet-base-v2",
    "sentence-transformers/multi-qa-mpnet-base-dot-v1",
    "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
    "intfloat/multilingual-e5-large",
    "intfloat/multilingual-e5-base",
    "intfloat/multilingual-e5-small",
    "BAAI/bge-large-en-v1.5",
    "BAAI/bge-base-en-v1.5",
    "BAAI/bge-small-en-v1.5",
]


class HuggingFaceDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(HF_MODELS),
        placeholder="sentence-transformers/all-MiniLM-L6-v2",
        description=MultilingualString(
            en="Name of the pre-trained HuggingFace model to use.",
            es="Nombre del modelo HuggingFace pre-entrenado a utilizar.",
        ),
    )  # type: ignore

    max_length: schema_field(
        int_field(ge=1),
        placeholder=512,
        description=MultilingualString(
            en="Maximum sequence length for tokenization.",
            es="Longitud máxima de secuencia para tokenización.",
        ),
    )  # type: ignore

    batch_size: schema_field(
        int_field(ge=1),
        placeholder=32,
        description=MultilingualString(
            en="Number of samples to process at once.",
            es="Número de muestras a procesar a la vez.",
        ),
    )  # type: ignore

    device: schema_field(
        enum_field(["cpu", "cuda"]),
        placeholder="cpu",
        description=MultilingualString(
            en="Device to run the model on.",
            es="Dispositivo para ejecutar el modelo.",
        ),
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(["mean", "cls", "max"]),
        placeholder="mean",
        description=MultilingualString(
            en="Pooling strategy to aggregate token embeddings.",
            es="Estrategia de pooling para agregar embeddings de tokens.",
        ),
    )  # type: ignore

    similarity_metric: schema_field(
        enum_field(enum=METRICS),
        placeholder="cosine",
        description=MultilingualString(
            en="Distance metric for comparing dense vectors.",
            es="Métrica de distancia para comparar vectores densos.",
        ),
    )  # type: ignore

    top_k: schema_field(
        int_field(gt=0),
        placeholder=5,
        description=MultilingualString(
            en="Number of chunks to select.",
            es="Número de fragmentos a seleccionar.",
        ),
    )  # type: ignore


class HuggingFaceDenseRetriever(DenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = HuggingFaceDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="HuggingFace Embedding Retriever",
        es="Recuperador por Embeddings HuggingFace",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using HuggingFace embeddings for similarity search.",
        es="Recuperador denso que usa embeddings HuggingFace para búsqueda por similitud.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init_model(self) -> None:
        from DashAI.back.models.RAG.embeddings.dense.huggingface_embedding import (
            HuggingFaceEmbedding,
        )
        model_name = self.params.pop("model_name")
        max_length = self.params.pop("max_length")
        batch_size = self.params.pop("batch_size")
        device = self.params.pop("device")
        pooling_strategy = self.params.pop("pooling_strategy")
        embedding = HuggingFaceEmbedding(
            model_name=model_name,
            max_length=max_length,
            batch_size=batch_size,
            device=device,
            pooling_strategy=pooling_strategy,
        )
        self._init_embedding(embedding)
