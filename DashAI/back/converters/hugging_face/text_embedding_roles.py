"""Roles an embedding converter encodes text for.

This module sits outside the ``text_embedding`` package on purpose: the RAG
retriever layer imports these names, and importing a submodule of the package
would execute its ``__init__`` and pull every converter (and its model imports)
into the import graph before the retriever modules have finished loading.
"""

PASSAGE = "passage"
QUERY = "query"
ROLES = (PASSAGE, QUERY)
