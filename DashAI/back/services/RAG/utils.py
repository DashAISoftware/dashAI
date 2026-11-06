"""Shared utilities for RAG services.

Provides deterministic parameter normalisation and hashing used
across Prompt, LLM, and other RAG services, plus the corpus content hash that
gives fitted artifacts a session-independent identity.
"""

import hashlib
import json
from typing import Any, Dict


def normalize_params(params: dict[str, Any]) -> dict[str, Any]:
    """Recursively sort all dict keys for deterministic serialization.

    Uses a JSON round-trip with ``sort_keys=True`` to ensure identical
    JSON text for semantically equivalent parameter dicts, even when
    they contain nested dicts with non-deterministic key ordering.

    Args:
        params: Parameter dict to normalize.

    Returns:
        A new dict with all keys (including nested) in sorted order.
    """
    return json.loads(json.dumps(params, sort_keys=True))


def build_parameters_hash(params: dict[str, Any]) -> str:
    """Build a deterministic SHA-256 hash of the parameters dict.

    Uses ``json.dumps`` with ``sort_keys=True`` for recursive key
    sorting, matching the hash computation used in the migration.

    Args:
        params: Parameter dict to hash.

    Returns:
        Hex digest of the SHA-256 hash.
    """
    return hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()


def build_corpus_content_hash(chunks: Dict[int, Dict[int, Any]]) -> str:
    """Build a SHA-256 hash of a corpus' content, independent of database ids.

    Two sessions that chunk the same documents the same way produce the same
    hash, which is what lets fitted artifacts (sparse matrices, embedding
    matrices) be shared between them. Chunk database ids are deliberately
    excluded: they are per-session rowids that identify nothing about the
    content, so including them would defeat the reuse.

    Documents are walked in ascending id order and their chunks in ascending
    position order, so the digest does not depend on dict insertion order.

    Args:
        chunks: Nested ``{document_id: {position: chunk}}`` mapping. Each chunk
            must expose ``document_id``, ``document_position`` and ``hash``.

    Returns:
        The full hexadecimal SHA-256 digest.
    """
    digest = hashlib.sha256()
    for document_id in sorted(chunks):
        document_chunks = chunks[document_id]
        for position in sorted(document_chunks):
            chunk = document_chunks[position]
            digest.update(
                json.dumps(
                    {
                        "document_id": chunk.document_id,
                        "document_position": chunk.document_position,
                        "hash": chunk.hash,
                    },
                    sort_keys=True,
                ).encode()
            )
            digest.update(b"\n")
    return digest.hexdigest()
