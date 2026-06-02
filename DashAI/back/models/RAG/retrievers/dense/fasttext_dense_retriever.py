from DashAI.back.core.schema_fields import (
    BaseSchema,
    enum_field,
    int_field,
    schema_field,
)
from DashAI.back.core.utils import MultilingualString
from DashAI.back.models.RAG.embeddings.dense.fasttext_embedding import FastTextEmbedding
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import DenseRetriever

METRICS = ["cityblock", "cosine", "euclidean", "l1", "l2", "manhattan"]


class FastTextDenseRetrieverSchema(BaseSchema):
    model_name: schema_field(
        enum_field(["facebook/fasttext-es-vectors", "facebook/fasttext-en-vectors"]),
        placeholder="facebook/fasttext-en-vectors",
        description=MultilingualString(
            en="Name of the pre-trained FastText model to use.",
            es="Nombre del modelo FastText pre-entrenado a utilizar.",
        ),
    )  # type: ignore

    pooling_strategy: schema_field(
        enum_field(["mean", "max"]),
        placeholder="mean",
        description=MultilingualString(
            en="Pooling strategy to aggregate word vectors.",
            es="Estrategia de pooling para agregar vectores de palabras.",
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


class FastTextDenseRetriever(DenseRetriever):
    FLAGS: list[str] = []
    SCHEMA = FastTextDenseRetrieverSchema
    DISPLAY_NAME: str = MultilingualString(
        en="FastText Embedding Retriever",
        es="Recuperador por Embeddings FastText",
    )
    DESCRIPTION: str = MultilingualString(
        en="Dense retriever using FastText embeddings for similarity search.",
        es="Recuperador denso que usa embeddings FastText para búsqueda por similitud.",
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def init_model(self) -> None:
        from DashAI.back.models.RAG.embeddings.dense.fasttext_embedding import (
            FastTextEmbedding,
        )
        model_name = self.params.pop("model_name")
        pooling_strategy = self.params.pop("pooling_strategy")
        embedding = FastTextEmbedding(
            model_name=model_name,
            pooling_strategy=pooling_strategy,
        )
        self._init_embedding(embedding)
