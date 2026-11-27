"""Names of the sub-folders of the RAG storage root.

Every module that writes or reads a fitted artifact folder imports its name
from here, so the layout is spelled out in one place.
"""

#: Sub-folder that holds the fitted sparse retrievers, one folder per fit.
SPARSE_RETRIEVERS_DIRNAME = "sparse_retrievers"

#: Sub-folder that holds the embedding matrices, one folder per document and model.
EMBEDDINGS_DIRNAME = "embeddings"

#: Sub-folder that holds the chunk sets, one folder per chunk set and document.
CHUNK_SETS_DIRNAME = "chunk_sets"
