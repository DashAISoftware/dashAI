"""Post-index cleanup removes what a session's stale index left behind.

The cleanup runs after every successful index. It is scoped to one session:
only rows reachable from that session's own pipeline and chunk sets are
candidates, shared folders and embedding models survive while another row still
uses them, malformed input raises before anything is deleted, and a failure
leaves both the database and the disk as they were. Every folder it removes
lies inside the RAG storage root.
"""

import contextlib
import logging
import os
import subprocess
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import DashAI.back.job.RAG_index_job as index_job_module
import DashAI.back.job.RAG_job as rag_job_module
from DashAI.back.core.enums.status import RunStatus
from DashAI.back.dependencies.database.models import (
    GenerativeProcess,
    GenerativeSession,
    ProcessData,
    RAGChunkSet,
    RAGChunkSetDocument,
    RAGDenseRetriever,
    RAGEmbeddingMatrix,
    RAGEmbeddingModel,
    RAGPipeline,
    RAGRetriever,
    RAGRetrieverChild,
    RAGSparseRetriever,
)
from DashAI.back.job.base_job import JobError
from DashAI.back.job.RAG_index_job import RAGIndexJob
from DashAI.back.job.RAG_job import RAGJob
from DashAI.back.services.RAG import cleanup_service
from DashAI.back.services.RAG.chunking_service import chunk_document_dir
from DashAI.back.services.RAG.cleanup_service import (
    CleanupService,
    IndexCleanupSummary,
)
from DashAI.back.services.RAG.setup_service import SetupService
from tests.back.RAG.conftest import (
    _insert_data_document,
    _insert_rag_session,
    bm25_retriever_params,
    rag_session_columns,
    write_test_doc_file,
)

# Fixtures and helpers of the indexing tests, used by the job-level tests below.
from tests.back.RAG.test_RAG_indexing import (  # noqa: F401
    _create_session,
    _create_session_with_document,
    _register_stub_llm,
)

# Chat-turn helpers, used by the RAGJob call-site tests below.
from tests.back.RAG.test_RAG_job_completes_flow import (  # noqa: F401
    DOC_TEXT,
    StubLLM,
    _create_test_document,
    _frontend_session_parameters,
)

SPARSE_CLASS = "BM25Retriever"
DENSE_CLASS = "DenseEmbeddingRetriever"
COMPOSITE_CLASS = "ParallelRetriever"
EMBEDDING_CLASS = "SentenceTransformerEmbedding"
STALE_K1 = 1.2
LIVE_K1 = 1.5
# Unusual values, so no other test in this module shares the fitted folders.
OLD_K1 = 1.37
NEW_K1 = 1.91
UNKNOWN_BRIDGE_ID = 999_999
# Storage sub-folders of the RAG root, spelled out here on purpose: the tests
# check the layout the services write, not the constants they import.
SPARSE_DIR = "sparse_retrievers"
EMBEDDINGS_DIR = "embeddings"
CHUNK_SETS_DIR = "chunk_sets"
#: Ways of spelling one existing Windows folder differently.
SPELLINGS = [
    pytest.param("forward_slashes", id="forward_slashes"),
    pytest.param("trailing_separator", id="trailing_separator"),
    pytest.param(
        "drive_case",
        id="drive_case",
        marks=pytest.mark.skipif(os.name != "nt", reason="Windows drive letters"),
    ),
]


class _Cancelled(BaseException):
    """Stands in for the queue cancelling a running job."""


@dataclass(frozen=True)
class _Counts:
    """Row counts of every table the cleanup may touch."""

    retrievers: int
    retriever_children: int
    sparse_rows: int
    dense_rows: int
    matrices: int
    models: int
    chunk_sets: int


@dataclass(frozen=True)
class _Index:
    """Ids and folders of one session with a live index and a stale one."""

    session_id: int
    pipeline_id: int
    document_id: int
    chunk_set_id: int
    root_id: int
    stale_sparse_id: int
    live_sparse_id: int
    stale_dense_id: int
    live_dense_id: int
    stale_model_id: int
    live_model_id: int
    stale_sparse_folder: Path
    live_sparse_folder: Path
    stale_matrix_folder: Path
    live_matrix_folder: Path
    rag_path: Path


def _rag(tmp_path: Path) -> Path:
    """Return the RAG storage root of a test, which holds every fitted folder."""
    return tmp_path / "rag"


def _spell(path: Path, spelling: str) -> str:
    """Spell an existing folder in another way that names the same folder."""
    text = str(path)
    if spelling == "forward_slashes":
        return text.replace("\\", "/")
    if spelling == "trailing_separator":
        return text + os.sep
    if spelling == "drive_case":
        return text[0].swapcase() + text[1:]
    raise ValueError(f"Unknown spelling {spelling!r}.")


def _pipeline(db: Session, session_id: int) -> int:
    """Insert the pipeline row of a session and return its id."""
    pipeline = RAGPipeline(session_id=session_id, name="")
    db.add(pipeline)
    db.flush()
    return pipeline.id


def _chunk_set(db: Session, session_id: int, document_id: int, rag: Path) -> int:
    """Insert a chunk set with one stored chunk folder under ``rag``."""
    chunk_set = RAGChunkSet(
        signature=uuid.uuid4().hex, parameters={}, session_id=session_id
    )
    db.add(chunk_set)
    db.flush()
    folder = chunk_document_dir(rag, chunk_set.id, document_id)
    folder.mkdir(parents=True, exist_ok=True)
    db.add(
        RAGChunkSetDocument(
            chunk_set_id=chunk_set.id,
            document_id=document_id,
            path=str(folder),
            n_chunks=1,
        )
    )
    db.flush()
    return chunk_set.id


def _sparse_bridge(
    db: Session, pipeline_id: int, chunk_set_id: int, storage: Path, k1: float
) -> int:
    """Insert a sparse retriever with its storage folder and return the bridge id."""
    bridge = RAGRetriever(class_name=SPARSE_CLASS, pipeline_id=pipeline_id)
    db.add(bridge)
    db.flush()
    storage.mkdir(parents=True, exist_ok=True)
    db.add(
        RAGSparseRetriever(
            bridge_id=bridge.id,
            chunk_set_id=chunk_set_id,
            class_name=SPARSE_CLASS,
            parameters={"k1": k1},
            storage_folder=str(storage),
        )
    )
    db.flush()
    return bridge.id


def _embedding_model(db: Session, label: str) -> int:
    """Insert an embedding model and return its id."""
    model = RAGEmbeddingModel(class_name=EMBEDDING_CLASS, parameters={"label": label})
    db.add(model)
    db.flush()
    return model.id


def _matrix(
    db: Session, document_id: int, chunk_set_id: int, model_id: int, storage: Path
) -> int:
    """Insert an embedding matrix row with its folder and return its id."""
    storage.mkdir(parents=True, exist_ok=True)
    matrix = RAGEmbeddingMatrix(
        document_id=document_id,
        chunk_set_id=chunk_set_id,
        embedding_model_id=model_id,
        storage_folder=str(storage),
        matrix_shape=[1, 1],
    )
    db.add(matrix)
    db.flush()
    return matrix.id


def _dense_bridge(
    db: Session, pipeline_id: int, chunk_set_id: int, model_id: int, label: str
) -> int:
    """Insert a dense retriever detail and return its bridge id."""
    bridge = RAGRetriever(class_name=DENSE_CLASS, pipeline_id=pipeline_id)
    db.add(bridge)
    db.flush()
    db.add(
        RAGDenseRetriever(
            bridge_id=bridge.id,
            chunk_set_id=chunk_set_id,
            class_name=DENSE_CLASS,
            parameters={"label": label},
            embedding_model_id=model_id,
        )
    )
    db.flush()
    return bridge.id


def _bare_bridge(db: Session, pipeline_id: int) -> int:
    """Insert a bridge with neither a detail nor children, and return its id."""
    bridge = RAGRetriever(class_name=SPARSE_CLASS, pipeline_id=pipeline_id)
    db.add(bridge)
    db.flush()
    return bridge.id


def _composite(db: Session, pipeline_id: int, child_ids: list[int]) -> int:
    """Insert a composite over the given bridges, in order, and return its id."""
    parent = RAGRetriever(class_name=COMPOSITE_CLASS, pipeline_id=pipeline_id)
    db.add(parent)
    db.flush()
    for order, child_id in enumerate(child_ids):
        db.add(
            RAGRetrieverChild(parent_id=parent.id, child_id=child_id, child_order=order)
        )
    db.flush()
    return parent.id


def _build_index(
    db: Session, tmp_path: Path, session_id: int, document_id: int
) -> _Index:
    """Build a session whose live index sits beside its stale rows and folders.

    The live tree is a composite over a live sparse and a live dense retriever.
    The stale rows are an old sparse retriever (other parameters), an old dense
    retriever with its own embedding model, and their folders, all under the
    RAG storage root.
    """
    rag = _rag(tmp_path)
    pipeline_id = _pipeline(db, session_id)
    chunk_set_id = _chunk_set(db, session_id, document_id, rag)
    stale_sparse_folder = rag / SPARSE_DIR / "stale"
    live_sparse_folder = rag / SPARSE_DIR / "live"
    stale_sparse = _sparse_bridge(
        db, pipeline_id, chunk_set_id, stale_sparse_folder, STALE_K1
    )
    live_sparse = _sparse_bridge(
        db, pipeline_id, chunk_set_id, live_sparse_folder, LIVE_K1
    )
    stale_model = _embedding_model(db, "stale")
    live_model = _embedding_model(db, "live")
    stale_matrix_folder = rag / EMBEDDINGS_DIR / "stale"
    live_matrix_folder = rag / EMBEDDINGS_DIR / "live"
    _matrix(db, document_id, chunk_set_id, stale_model, stale_matrix_folder)
    _matrix(db, document_id, chunk_set_id, live_model, live_matrix_folder)
    stale_dense = _dense_bridge(db, pipeline_id, chunk_set_id, stale_model, "stale")
    live_dense = _dense_bridge(db, pipeline_id, chunk_set_id, live_model, "live")
    root = _composite(db, pipeline_id, [live_sparse, live_dense])
    db.commit()
    return _Index(
        session_id=session_id,
        pipeline_id=pipeline_id,
        document_id=document_id,
        chunk_set_id=chunk_set_id,
        root_id=root,
        stale_sparse_id=stale_sparse,
        live_sparse_id=live_sparse,
        stale_dense_id=stale_dense,
        live_dense_id=live_dense,
        stale_model_id=stale_model,
        live_model_id=live_model,
        stale_sparse_folder=stale_sparse_folder,
        live_sparse_folder=live_sparse_folder,
        stale_matrix_folder=stale_matrix_folder,
        live_matrix_folder=live_matrix_folder,
        rag_path=rag,
    )


def _other_session_with_chunk_set(
    db: Session, tmp_path: Path, document_id: int
) -> tuple[int, int]:
    """Create a second session with a pipeline and a chunk set of its own."""
    other = _insert_rag_session(db, f"other_{uuid.uuid4().hex[:8]}")
    pipeline_id = _pipeline(db, other.id)
    chunk_set_id = _chunk_set(db, other.id, document_id, _rag(tmp_path))
    db.commit()
    return pipeline_id, chunk_set_id


def _counts(db: Session) -> _Counts:
    """Count the rows of every table the cleanup may touch."""
    return _Counts(
        retrievers=db.query(RAGRetriever).count(),
        retriever_children=db.query(RAGRetrieverChild).count(),
        sparse_rows=db.query(RAGSparseRetriever).count(),
        dense_rows=db.query(RAGDenseRetriever).count(),
        matrices=db.query(RAGEmbeddingMatrix).count(),
        models=db.query(RAGEmbeddingModel).count(),
        chunk_sets=db.query(RAGChunkSet).count(),
    )


def _cleanup(db: Session, index: _Index) -> IndexCleanupSummary:
    """Run the cleanup for an index built by :func:`_build_index`."""
    service = CleanupService(db, rag_path=index.rag_path)
    return service.cleanup_after_reindex(index.session_id, index.root_id)


# ===================================================================
# Stale rows of the indexed session
# ===================================================================


def test_stale_rows_and_folders_are_released_after_commit(
    orm_db, tmp_path, monkeypatch
):
    """Old sparse and dense rows go with their folders, and only after commit."""
    session = _insert_rag_session(orm_db, "reindex_release")
    document = _insert_data_document(orm_db, tmp_path / "docs", "release.txt", ["r"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    seen_at_commit: list[tuple[bool, bool]] = []
    real_commit = orm_db.commit

    def commit_and_record() -> None:
        """Record whether the folders still exist, then commit for real."""
        seen_at_commit.append(
            (index.stale_sparse_folder.exists(), index.stale_matrix_folder.exists())
        )
        real_commit()

    monkeypatch.setattr(orm_db, "commit", commit_and_record)

    result = _cleanup(orm_db, index)

    assert seen_at_commit == [(True, True)], "folders must outlive the transaction"
    assert orm_db.get(RAGRetriever, index.stale_sparse_id) is None
    assert orm_db.get(RAGRetriever, index.stale_dense_id) is None
    assert orm_db.get(RAGEmbeddingModel, index.stale_model_id) is None
    assert orm_db.get(RAGRetriever, index.root_id) is not None
    assert orm_db.get(RAGRetriever, index.live_sparse_id) is not None
    assert orm_db.get(RAGRetriever, index.live_dense_id) is not None
    assert orm_db.get(RAGEmbeddingModel, index.live_model_id) is not None
    assert not index.stale_sparse_folder.exists()
    assert not index.stale_matrix_folder.exists()
    assert index.live_sparse_folder.exists()
    assert index.live_matrix_folder.exists()
    assert result.bridges == 2
    assert result.embedding_matrices == 1
    assert result.embedding_models == 1
    assert result.chunk_sets == 0


def test_stale_composite_is_removed_and_the_live_tree_survives(orm_db, tmp_path):
    """A composite left by an earlier index goes; the live tree keeps its links."""
    session = _insert_rag_session(orm_db, "reindex_composite")
    document = _insert_data_document(orm_db, tmp_path / "docs", "composite.txt", ["c"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    stale_composite = _composite(
        orm_db, index.pipeline_id, [index.live_sparse_id, index.stale_sparse_id]
    )
    orm_db.commit()

    _cleanup(orm_db, index)

    assert orm_db.get(RAGRetriever, stale_composite) is None
    assert orm_db.get(RAGRetriever, index.stale_sparse_id) is None
    assert orm_db.get(RAGRetriever, index.live_sparse_id) is not None
    links = {
        (link.parent_id, link.child_id) for link in orm_db.query(RAGRetrieverChild)
    }
    assert links == {
        (index.root_id, index.live_sparse_id),
        (index.root_id, index.live_dense_id),
    }
    assert index.live_sparse_folder.exists()


def test_stale_chunk_set_of_the_same_session_is_invalidated(orm_db, tmp_path):
    """A chunk set the session no longer uses goes with what was fitted on it."""
    session = _insert_rag_session(orm_db, "reindex_chunks")
    document = _insert_data_document(orm_db, tmp_path / "docs", "chunks.txt", ["k"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    old_set = _chunk_set(orm_db, session.id, document.id, index.rag_path)
    old_folder = index.rag_path / SPARSE_DIR / "old_set"
    old_sparse = _sparse_bridge(orm_db, index.pipeline_id, old_set, old_folder, LIVE_K1)
    orm_db.commit()
    old_chunk_folder = index.rag_path / CHUNK_SETS_DIR / str(old_set)

    result = _cleanup(orm_db, index)

    assert orm_db.get(RAGChunkSet, old_set) is None
    assert orm_db.get(RAGRetriever, old_sparse) is None
    assert not old_folder.exists()
    assert not old_chunk_folder.exists()
    assert orm_db.get(RAGChunkSet, index.chunk_set_id) is not None
    assert result.chunk_sets == 1


# ===================================================================
# Shared artifacts
# ===================================================================


def test_artifacts_another_session_references_are_kept(orm_db, tmp_path):
    """A folder or model another session still uses survives the cleanup."""
    session = _insert_rag_session(orm_db, "reindex_shared_owner")
    document = _insert_data_document(orm_db, tmp_path / "docs", "shared.txt", ["s"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    other = _insert_rag_session(orm_db, "reindex_shared_other")
    other_pipeline = _pipeline(orm_db, other.id)
    other_set = _chunk_set(orm_db, other.id, document.id, index.rag_path)
    _sparse_bridge(
        orm_db, other_pipeline, other_set, index.stale_sparse_folder, STALE_K1
    )
    _sparse_bridge(orm_db, other_pipeline, other_set, index.live_sparse_folder, LIVE_K1)
    _matrix(
        orm_db, document.id, other_set, index.stale_model_id, index.stale_matrix_folder
    )
    _matrix(
        orm_db, document.id, other_set, index.live_model_id, index.live_matrix_folder
    )
    orm_db.commit()

    result = _cleanup(orm_db, index)

    assert orm_db.get(RAGRetriever, index.stale_sparse_id) is None
    assert (
        orm_db.query(RAGSparseRetriever).filter_by(chunk_set_id=other_set).count() == 2
    )
    assert index.stale_sparse_folder.exists(), "the other session still uses it"
    assert orm_db.get(RAGEmbeddingModel, index.stale_model_id) is not None
    assert (
        orm_db.query(RAGEmbeddingMatrix).filter_by(chunk_set_id=other_set).count() == 2
    )
    assert index.stale_matrix_folder.exists(), "the other session still uses it"
    assert index.live_matrix_folder.exists()
    assert result.embedding_models == 0
    assert result.embedding_matrices == 1


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_sparse_folder_another_row_spells_differently_is_kept(
    orm_db, tmp_path, spelling
):
    """A folder a live row reaches under another spelling still counts as used."""
    session = _insert_rag_session(orm_db, f"spelling_sparse_{spelling}")
    document = _insert_data_document(
        orm_db, tmp_path / "docs", f"sp_{spelling}.txt", ["p"]
    )
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    other = _insert_rag_session(orm_db, f"spelling_sparse_other_{spelling}")
    other_pipeline = _pipeline(orm_db, other.id)
    other_set = _chunk_set(orm_db, other.id, document.id, index.rag_path)
    bridge_id = _sparse_bridge(
        orm_db, other_pipeline, other_set, index.stale_sparse_folder, LIVE_K1
    )
    other_row = orm_db.query(RAGSparseRetriever).filter_by(bridge_id=bridge_id).one()
    other_row.storage_folder = _spell(index.stale_sparse_folder, spelling)
    orm_db.commit()

    _cleanup(orm_db, index)

    assert orm_db.get(RAGRetriever, index.stale_sparse_id) is None
    assert index.stale_sparse_folder.exists(), "a live row still reaches the folder"


@pytest.mark.parametrize("spelling", SPELLINGS)
def test_embedding_folder_another_row_spells_differently_is_kept(
    orm_db, tmp_path, spelling
):
    """A matrix folder another row reaches under another spelling is kept."""
    session = _insert_rag_session(orm_db, f"spelling_matrix_{spelling}")
    document = _insert_data_document(
        orm_db, tmp_path / "docs", f"mx_{spelling}.txt", ["q"]
    )
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    other = _insert_rag_session(orm_db, f"spelling_matrix_other_{spelling}")
    other_set = _chunk_set(orm_db, other.id, document.id, index.rag_path)
    matrix_id = _matrix(
        orm_db, document.id, other_set, index.live_model_id, index.live_matrix_folder
    )
    other_row = orm_db.get(RAGEmbeddingMatrix, matrix_id)
    other_row.storage_folder = _spell(index.stale_matrix_folder, spelling)
    orm_db.commit()

    _cleanup(orm_db, index)

    assert orm_db.get(RAGEmbeddingMatrix, matrix_id) is not None
    assert index.stale_matrix_folder.exists(), "another row still reaches the folder"


@pytest.fixture
def folder_link() -> Iterator[Callable[[Path, Path], None]]:
    """Yield a maker of folder links, and remove those links afterwards."""
    links: list[Path] = []

    def make(link: Path, target: Path) -> None:
        """Create ``link`` as a folder link that names ``target``."""
        _make_folder_link(link, target)
        links.append(link)

    yield make
    for link in links:
        with contextlib.suppress(OSError):
            os.rmdir(link)


def _make_folder_link(link: Path, target: Path) -> None:
    """Create ``link`` as a directory junction, or a symlink, to ``target``.

    The test is skipped when neither can be created on this machine.
    """
    try:
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
            timeout=60,
        )
        return
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        os.symlink(target, link, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"Cannot create a folder link here: {error}")


def test_folder_reached_through_a_junction_is_kept(
    orm_db, tmp_path, monkeypatch, folder_link
):
    """A folder a row reaches through a junction is in use, whatever the spelling."""
    session = _insert_rag_session(orm_db, "spelling_junction")
    document = _insert_data_document(orm_db, tmp_path / "docs", "junction.txt", ["j"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    alias = index.rag_path / SPARSE_DIR / "alias"
    folder_link(alias, index.stale_sparse_folder)
    other = _insert_rag_session(orm_db, "spelling_junction_other")
    other_pipeline = _pipeline(orm_db, other.id)
    other_set = _chunk_set(orm_db, other.id, document.id, index.rag_path)
    _sparse_bridge(orm_db, other_pipeline, other_set, alias, LIVE_K1)
    stale_row = (
        orm_db.query(RAGSparseRetriever)
        .filter_by(bridge_id=index.stale_sparse_id)
        .one()
    )
    # The stale row stores a path relative to the working directory, the live row
    # the absolute junction path: both name the same folder.
    stale_row.storage_folder = os.path.join("rag", SPARSE_DIR, "stale")
    orm_db.commit()
    monkeypatch.chdir(tmp_path)

    _cleanup(orm_db, index)

    assert orm_db.get(RAGRetriever, index.stale_sparse_id) is None
    assert index.stale_sparse_folder.exists(), "a live row still reaches the folder"
    assert alias.is_dir(), "the live row's junction is untouched"


def test_cleanup_leaves_artifacts_no_row_of_the_session_points_at(orm_db, tmp_path):
    """Scope is the session: a model another session committed is not a candidate."""
    session = _insert_rag_session(orm_db, "reindex_scope")
    document = _insert_data_document(orm_db, tmp_path / "docs", "scope.txt", ["x"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    in_flight_model = _embedding_model(orm_db, "in_flight")
    unreferenced_folder = index.rag_path / SPARSE_DIR / "sparse_retriever_id-free"
    unreferenced_folder.mkdir(parents=True)
    orm_db.commit()

    result = _cleanup(orm_db, index)

    assert orm_db.get(RAGEmbeddingModel, in_flight_model) is not None
    assert unreferenced_folder.exists(), "no global sweep of the disk"
    assert result.embedding_models == 1


# ===================================================================
# Orphan matrices of a stale chunk set
# ===================================================================


def test_stale_chunk_set_matrix_without_a_dense_retriever_is_released(orm_db, tmp_path):
    """A matrix with no dense link must not block deleting its chunk set."""
    session = _insert_rag_session(orm_db, "orphan_matrix")
    document = _insert_data_document(orm_db, tmp_path / "docs", "orphan.txt", ["o"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    old_set = _chunk_set(orm_db, session.id, document.id, index.rag_path)
    orphan_model = _embedding_model(orm_db, "orphan")
    orphan_folder = index.rag_path / EMBEDDINGS_DIR / "orphan"
    orphan_matrix = _matrix(orm_db, document.id, old_set, orphan_model, orphan_folder)
    orm_db.commit()

    result = _cleanup(orm_db, index)

    assert orm_db.get(RAGChunkSet, old_set) is None
    assert orm_db.get(RAGEmbeddingMatrix, orphan_matrix) is None
    assert orm_db.get(RAGEmbeddingModel, orphan_model) is None
    assert not orphan_folder.exists()
    assert result.chunk_sets == 1


def test_orphan_matrix_keeps_a_folder_another_row_uses(orm_db, tmp_path):
    """An orphan's folder and model survive while another session's row uses them."""
    session = _insert_rag_session(orm_db, "orphan_shared")
    document = _insert_data_document(orm_db, tmp_path / "docs", "orphan_s.txt", ["t"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    old_set = _chunk_set(orm_db, session.id, document.id, index.rag_path)
    shared_model = _embedding_model(orm_db, "shared_orphan")
    shared_folder = index.rag_path / EMBEDDINGS_DIR / "shared_orphan"
    _matrix(orm_db, document.id, old_set, shared_model, shared_folder)
    other = _insert_rag_session(orm_db, "orphan_shared_other")
    other_set = _chunk_set(orm_db, other.id, document.id, index.rag_path)
    other_matrix = _matrix(orm_db, document.id, other_set, shared_model, shared_folder)
    orm_db.commit()

    _cleanup(orm_db, index)

    assert orm_db.get(RAGChunkSet, old_set) is None
    assert shared_folder.exists(), "the other session's matrix still uses it"
    assert orm_db.get(RAGEmbeddingMatrix, other_matrix) is not None
    assert orm_db.get(RAGEmbeddingModel, shared_model) is not None


# ===================================================================
# Containment under the RAG storage root
# ===================================================================


def test_sparse_row_outside_the_rag_root_is_deleted_and_its_folder_kept(
    orm_db, tmp_path, caplog
):
    """A stale row pointing outside the RAG root goes; the folder is not touched."""
    session = _insert_rag_session(orm_db, "contain_sparse")
    document = _insert_data_document(orm_db, tmp_path / "docs", "contain.txt", ["n"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    precious = tmp_path / "outside" / "sparse"
    precious.mkdir(parents=True)
    (precious / "precious.txt").write_text("keep me", encoding="utf-8")
    stale = _sparse_bridge(orm_db, index.pipeline_id, index.chunk_set_id, precious, 1.1)
    orm_db.commit()

    with caplog.at_level(logging.WARNING, logger=cleanup_service.__name__):
        _cleanup(orm_db, index)

    assert orm_db.get(RAGRetriever, stale) is None
    assert (precious / "precious.txt").read_text(encoding="utf-8") == "keep me"
    assert any(
        record.levelno == logging.WARNING and "outside" in record.getMessage()
        for record in caplog.records
    )


def test_chunk_path_outside_its_chunk_set_is_not_removed(orm_db, tmp_path, caplog):
    """A chunk row whose parent is an unrelated folder never removes that folder."""
    session = _insert_rag_session(orm_db, "contain_chunk")
    document = _insert_data_document(orm_db, tmp_path / "docs", "chunk_c.txt", ["c"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    old_set = _chunk_set(orm_db, session.id, document.id, index.rag_path)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    (unrelated / "doc.arrow").write_bytes(b"data")
    row = orm_db.query(RAGChunkSetDocument).filter_by(chunk_set_id=old_set).one()
    row.path = str(unrelated / "doc.arrow")
    orm_db.commit()

    with caplog.at_level(logging.WARNING, logger=cleanup_service.__name__):
        _cleanup(orm_db, index)

    assert orm_db.get(RAGChunkSet, old_set) is None
    assert (unrelated / "doc.arrow").exists()
    assert any(
        record.levelno == logging.WARNING and "outside" in record.getMessage()
        for record in caplog.records
    )


def test_chunk_folder_is_kept_with_a_warning_when_no_stored_path_is_inside_it(
    orm_db, tmp_path, caplog
):
    """With a RAG root, a chunk set whose paths all lie elsewhere keeps its folder."""
    session = _insert_rag_session(orm_db, f"keep_chunk_{uuid.uuid4().hex[:6]}")
    document = _insert_data_document(orm_db, tmp_path / "docs", "keep.txt", ["k"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    old_set = _chunk_set(orm_db, session.id, document.id, index.rag_path)
    chunk_folder = index.rag_path / CHUNK_SETS_DIR / str(old_set)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    row = orm_db.query(RAGChunkSetDocument).filter_by(chunk_set_id=old_set).one()
    row.path = str(elsewhere)
    orm_db.commit()

    with caplog.at_level(logging.WARNING, logger=cleanup_service.__name__):
        _cleanup(orm_db, index)

    assert orm_db.get(RAGChunkSet, old_set) is None
    assert chunk_folder.exists()
    assert any(
        "no stored chunk path lies inside" in record.getMessage()
        for record in caplog.records
    )


def test_cleanup_without_a_rag_path_is_refused(orm_db, tmp_path):
    """Without the storage root the removals cannot be checked, so nothing runs."""
    session = _insert_rag_session(orm_db, "contain_refused")
    document = _insert_data_document(orm_db, tmp_path / "docs", "refused.txt", ["r"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    before = _counts(orm_db)

    with pytest.raises(ValueError, match="rag_path"):
        CleanupService(orm_db).cleanup_after_reindex(index.session_id, index.root_id)

    assert _counts(orm_db) == before
    assert index.stale_sparse_folder.exists()


# ===================================================================
# Idempotence and malformed input
# ===================================================================


def test_a_second_cleanup_changes_nothing(orm_db, tmp_path):
    """Once the stale rows are gone, running the cleanup again is a no-op."""
    session = _insert_rag_session(orm_db, "reindex_idempotent")
    document = _insert_data_document(orm_db, tmp_path / "docs", "idem.txt", ["i"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    service = CleanupService(orm_db, rag_path=index.rag_path)
    service.cleanup_after_reindex(index.session_id, index.root_id)
    state = _counts(orm_db)

    second = service.cleanup_after_reindex(index.session_id, index.root_id)

    assert (
        second.chunk_sets,
        second.bridges,
        second.embedding_matrices,
        second.embedding_models,
    ) == (0, 0, 0, 0)
    assert _counts(orm_db) == state


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("unknown_root", "is not a retriever of session"),
        ("other_session_root", "is not a retriever of session"),
        ("bare_root", "neither a fitted detail"),
        ("foreign_chunk_set_root", "not owned by session"),
    ],
)
def test_malformed_live_root_raises_and_deletes_nothing(
    orm_db, tmp_path, case, message
):
    """A root that cannot describe this session's live index is refused outright."""
    session = _insert_rag_session(orm_db, f"malformed_{case}")
    document = _insert_data_document(orm_db, tmp_path / "docs", f"{case}.txt", ["m"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    other_pipeline, other_set = _other_session_with_chunk_set(
        orm_db, tmp_path, document.id
    )
    if case == "unknown_root":
        root_id = UNKNOWN_BRIDGE_ID
    elif case == "other_session_root":
        root_id = _sparse_bridge(
            orm_db, other_pipeline, other_set, tmp_path / "foreign_root", LIVE_K1
        )
    elif case == "bare_root":
        root_id = _bare_bridge(orm_db, index.pipeline_id)
    else:
        root_id = _sparse_bridge(
            orm_db, index.pipeline_id, other_set, tmp_path / "foreign_set", LIVE_K1
        )
    orm_db.commit()
    before = _counts(orm_db)

    with pytest.raises(ValueError, match=message):
        CleanupService(orm_db, rag_path=index.rag_path).cleanup_after_reindex(
            index.session_id, root_id
        )

    assert _counts(orm_db) == before
    assert index.stale_sparse_folder.exists()
    assert index.stale_matrix_folder.exists()


def test_a_session_without_a_pipeline_is_rejected(orm_db, tmp_path):
    """Without a pipeline there is no live index to protect, so nothing is guessed."""
    session = _insert_rag_session(orm_db, "reindex_no_pipeline")

    with pytest.raises(ValueError, match="has no pipeline"):
        CleanupService(orm_db, rag_path=_rag(tmp_path)).cleanup_after_reindex(
            session.id, UNKNOWN_BRIDGE_ID
        )


# ===================================================================
# Failure handling
# ===================================================================


@pytest.mark.parametrize("failure", ["commit", "mid_run"])
def test_a_failed_cleanup_keeps_rows_and_folders(
    orm_db, tmp_path, monkeypatch, failure
):
    """Any failure rolls back the rows and drops the queued folder removals."""
    session = _insert_rag_session(orm_db, f"failing_{failure}")
    document = _insert_data_document(orm_db, tmp_path / "docs", f"{failure}.txt", ["f"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    before = _counts(orm_db)
    if failure == "commit":

        def fail_commit() -> None:
            """Fail the commit that ends the cleanup."""
            raise RuntimeError("commit failed")

        monkeypatch.setattr(orm_db, "commit", fail_commit)
    else:

        def fail_guard(self, storage_folder, exclude_ids=()) -> bool:
            """Fail the folder guard in the middle of the cleanup."""
            raise RuntimeError("guard failed")

        monkeypatch.setattr(CleanupService, "_embedding_folder_in_use", fail_guard)

    with pytest.raises(RuntimeError):
        _cleanup(orm_db, index)

    assert _counts(orm_db) == before
    assert index.stale_sparse_folder.exists(), "a queued removal must be dropped"
    assert index.stale_matrix_folder.exists()


def test_the_entry_point_swallows_failures_but_not_cancellation(
    client: TestClient, tmp_path, monkeypatch, caplog
):
    """Cleanup errors are logged and dropped; a cancellation still propagates."""
    session_factory = client.app.container["session_factory"]
    registry = client.app.container["component_registry"]
    session_id = _create_session(client, "entry_point")

    def explode(self, session_id, live_root_bridge_id):
        """Fail the way a broken cleanup would."""
        raise RuntimeError("cleanup broke")

    monkeypatch.setattr(CleanupService, "cleanup_after_reindex", explode)
    with (
        caplog.at_level(logging.ERROR, logger=cleanup_service.__name__),
        session_factory() as db,
    ):
        cleanup_service.run_post_index_cleanup(
            db, registry, session_id, UNKNOWN_BRIDGE_ID, _rag(tmp_path)
        )
    assert any(record.exc_info for record in caplog.records)

    def cancel(self, session_id, live_root_bridge_id):
        """Raise the cancellation the queue delivers to a running job."""
        raise _Cancelled

    monkeypatch.setattr(CleanupService, "cleanup_after_reindex", cancel)
    with session_factory() as db, pytest.raises(_Cancelled):
        cleanup_service.run_post_index_cleanup(
            db, registry, session_id, UNKNOWN_BRIDGE_ID, _rag(tmp_path)
        )


def test_a_missing_live_root_is_logged_and_not_fatal(
    client: TestClient, tmp_path, caplog
):
    """A None root id is refused inside the guarded path, logged, and returned."""
    session_factory = client.app.container["session_factory"]
    registry = client.app.container["component_registry"]
    session_id = _create_session(client, "missing_root")

    with (
        caplog.at_level(logging.ERROR, logger=cleanup_service.__name__),
        session_factory() as db,
    ):
        result = cleanup_service.run_post_index_cleanup(
            db, registry, session_id, None, _rag(tmp_path)
        )

    assert result is None
    records = [record for record in caplog.records if record.exc_info]
    assert records, "the refusal must be logged with its traceback"
    assert "live root" in str(records[0].exc_info[1])


# ===================================================================
# Job level
# ===================================================================


def test_index_job_succeeds_when_the_post_index_cleanup_fails(
    client: TestClient, document_files: list[str], monkeypatch, caplog
):
    """A cleanup failure is logged; the index is complete and the job succeeds."""
    session_id, _ = _create_session_with_document(
        client, "cleanup_failure", document_files
    )

    def explode(self, session_id, live_root_bridge_id):
        """Fail the way a broken cleanup would."""
        raise RuntimeError("cleanup broke")

    monkeypatch.setattr(CleanupService, "cleanup_after_reindex", explode)
    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        result = RAGIndexJob(session_id=session_id).run()

    assert result["total_chunks"] > 0
    assert isinstance(result["chunk_set_id"], int)
    assert any(record.exc_info for record in caplog.records)
    status = client.get(f"/api/v1/rag/sessions/{session_id}/index-status").json()
    assert status["status"] == "indexed", status


def test_index_job_returns_its_result_when_the_live_root_is_missing(
    client: TestClient, document_files: list[str], monkeypatch, caplog
):
    """A missing root id is logged by the cleanup; the job still returns its result."""
    session_id, _ = _create_session_with_document(
        client, "index_no_root", document_files
    )
    original_build_index = SetupService.build_index

    def build_index_without_root(self, config, progress=None):
        """Build the index, then hand back a result with no root bridge id."""
        result = original_build_index(self, config, progress=progress)
        return SimpleNamespace(
            chunk_set_id=result.chunk_set_id,
            total_chunks=result.total_chunks,
            retriever=SimpleNamespace(db_record_id=None),
        )

    monkeypatch.setattr(SetupService, "build_index", build_index_without_root)
    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        result = RAGIndexJob(session_id=session_id).run()

    assert result["total_chunks"] > 0
    assert any(record.exc_info for record in caplog.records)


def test_index_job_passes_the_configured_rag_path_to_the_cleanup(
    client: TestClient, document_files: list[str], monkeypatch
):
    """The index job hands the configured RAG root to the post-index cleanup."""
    session_id, _ = _create_session_with_document(
        client, "index_rag_path", document_files
    )
    roots: list[int] = []
    original_build_index = SetupService.build_index

    def build_index(self, config, progress=None):
        """Build the index and remember the root bridge it produced."""
        result = original_build_index(self, config, progress=progress)
        roots.append(result.retriever.db_record_id)
        return result

    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(SetupService, "build_index", build_index)
    monkeypatch.setattr(
        index_job_module,
        "run_post_index_cleanup",
        lambda *args: calls.append(args[2:]),
    )

    RAGIndexJob(session_id=session_id).run()

    rag_path = client.app.container["config"]["RAG_PATH"]
    assert calls == [(session_id, roots[0], rag_path)]


def _raise_build_failure(error: BaseException):
    """Build a ``build_index`` replacement that raises ``error``."""

    def build_index(self, config, progress=None):
        """Raise the configured error in place of building an index."""
        raise error

    return build_index


def test_post_index_cleanup_does_not_run_when_indexing_fails(
    client: TestClient, document_files: list[str], monkeypatch
):
    """A failed index has nothing to clean up after; the cleanup is not invoked."""
    session_id, _ = _create_session_with_document(
        client, "cleanup_not_on_failure", document_files
    )
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        index_job_module,
        "run_post_index_cleanup",
        lambda *args, **kwargs: calls.append(args),
    )
    monkeypatch.setattr(
        SetupService, "build_index", _raise_build_failure(RuntimeError("bad"))
    )

    with pytest.raises(JobError):
        RAGIndexJob(session_id=session_id).run()

    assert calls == []


def test_post_index_cleanup_does_not_run_when_the_job_is_cancelled(
    client: TestClient, document_files: list[str], monkeypatch
):
    """Cancellation is a BaseException; it skips the cleanup and propagates."""
    session_id, _ = _create_session_with_document(
        client, "cleanup_not_on_cancel", document_files
    )
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        index_job_module,
        "run_post_index_cleanup",
        lambda *args, **kwargs: calls.append(args),
    )
    monkeypatch.setattr(SetupService, "build_index", _raise_build_failure(_Cancelled()))

    with pytest.raises(_Cancelled):
        RAGIndexJob(session_id=session_id).run()

    assert calls == []


@pytest.fixture
def document_files() -> Iterator[list[str]]:
    """Collect the document files a job test writes, and remove them afterwards."""
    paths: list[str] = []
    yield paths
    for path in paths:
        with contextlib.suppress(OSError):
            os.remove(path)


def _set_bm25_k1(client: TestClient, session_id: int, k1: float) -> None:
    """Give a session a BM25 retriever with the given ``k1`` weighting."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = db.get(GenerativeSession, session_id)
        parameters = dict(session.parameters)
        parameters["retriever_model"] = {
            "component": SPARSE_CLASS,
            "params": {**bm25_retriever_params(), "k1": k1},
        }
        session.parameters = parameters
        db.commit()


def _sparse_rows_of(client: TestClient, session_id: int) -> list[tuple[int, str]]:
    """Return ``(row id, storage folder)`` of every sparse row of a session."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        rows = (
            db.query(RAGSparseRetriever)
            .join(RAGRetriever, RAGSparseRetriever.bridge_id == RAGRetriever.id)
            .join(RAGPipeline, RAGRetriever.pipeline_id == RAGPipeline.id)
            .filter(RAGPipeline.session_id == session_id)
            .all()
        )
        return [(row.id, row.storage_folder) for row in rows]


def test_reindex_after_an_identity_change_releases_the_old_sparse_index(
    client: TestClient, document_files: list[str]
):
    """Changing BM25's weighting re-fits it; the old row and folder are released."""
    session_id, _ = _create_session_with_document(
        client, "reindex_identity", document_files
    )
    _set_bm25_k1(client, session_id, OLD_K1)
    RAGIndexJob(session_id=session_id).run()
    before = _sparse_rows_of(client, session_id)

    _set_bm25_k1(client, session_id, NEW_K1)
    RAGIndexJob(session_id=session_id).run()
    after = _sparse_rows_of(client, session_id)

    assert len(before) == 1, before
    assert len(after) == 1, after
    (old_id, old_folder), (new_id, new_folder) = before[0], after[0]
    assert new_id != old_id
    assert new_folder != old_folder
    assert not os.path.exists(old_folder), "the stale folder must be released"
    assert os.path.isdir(new_folder)


# ===================================================================
# Chat job call site
# ===================================================================


@pytest.fixture
def chat_stub_llm(client: TestClient) -> None:
    """Register the stub generation model the chat turns below use."""
    registry = client.app.container["component_registry"]
    if "StubLLM" not in registry:
        registry.register_component(StubLLM)


def _chat_process(
    client: TestClient, document_files: list[str], tag: str
) -> tuple[int, int]:
    """Create a RAG session with one document and one pending turn.

    Returns the session id and the process id.
    """
    suffix = f"_post_index_{tag}_{uuid.uuid4().hex[:6]}"
    doc_id = _create_test_document(client, suffix=suffix, text=DOC_TEXT)
    document_files.append(write_test_doc_file(suffix, DOC_TEXT))
    parameters = _frontend_session_parameters(
        doc_id, "BM25Retriever", "DefaultRAGGenerationPrompt"
    )
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        session = GenerativeSession(
            **rag_session_columns(parameters),
            name=f"post_index_{tag}",
            description=None,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        process = GenerativeProcess(session_id=session.id, status=RunStatus.NOT_STARTED)
        db.add(process)
        db.commit()
        db.refresh(process)
        db.add(
            ProcessData(
                process_id=process.id,
                is_input=True,
                data="Tell me about DashAI",
                data_type="str",
            )
        )
        db.commit()
        return session.id, process.id


def test_chat_turn_cleans_up_after_the_pipeline_is_built(
    client: TestClient, document_files: list[str], monkeypatch, chat_stub_llm
):
    """The turn cleans up once the pipeline exists, with its live root and RAG path."""
    session_id, process_id = _chat_process(client, document_files, "built")
    events: list[tuple[str, object]] = []
    original_build_pipeline = SetupService.build_pipeline

    def build_pipeline(self, config):
        """Build the pipeline and record its root bridge id."""
        pipeline = original_build_pipeline(self, config)
        events.append(("build", pipeline.retriever.get_id()))
        return pipeline

    monkeypatch.setattr(SetupService, "build_pipeline", build_pipeline)
    monkeypatch.setattr(
        rag_job_module,
        "run_post_index_cleanup",
        lambda *args: events.append(("cleanup", args[2:])),
    )

    RAGJob(generative_process_id=process_id).run()

    rag_path = client.app.container["config"]["RAG_PATH"]
    (build_kind, root_id), (cleanup_kind, cleanup_args) = events
    assert (build_kind, cleanup_kind) == ("build", "cleanup")
    assert cleanup_args == (session_id, root_id, rag_path)


def test_chat_turn_does_not_clean_up_when_the_pipeline_cannot_be_built(
    client: TestClient, document_files: list[str], monkeypatch, chat_stub_llm
):
    """A pipeline that fails to build has nothing to clean up after."""
    _session_id, process_id = _chat_process(client, document_files, "unbuilt")
    calls: list[tuple[object, ...]] = []

    def build_pipeline(self, config):
        """Fail the way a pipeline that cannot be built would."""
        raise RuntimeError("cannot build")

    monkeypatch.setattr(SetupService, "build_pipeline", build_pipeline)
    monkeypatch.setattr(
        rag_job_module,
        "run_post_index_cleanup",
        lambda *args: calls.append(args),
    )

    with pytest.raises(JobError):
        RAGJob(generative_process_id=process_id).run()

    assert calls == []


def test_chat_turn_finishes_when_the_post_index_cleanup_fails(
    client: TestClient, document_files: list[str], monkeypatch, caplog, chat_stub_llm
):
    """A cleanup failure is logged and the answered turn still finishes."""
    _session_id, process_id = _chat_process(client, document_files, "cleanup_fails")

    def explode(self, session_id, live_root_bridge_id):
        """Fail the way a broken cleanup would."""
        raise RuntimeError("cleanup broke")

    monkeypatch.setattr(CleanupService, "cleanup_after_reindex", explode)
    with caplog.at_level(logging.ERROR, logger=cleanup_service.__name__):
        RAGJob(generative_process_id=process_id).run()

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        process = db.get(GenerativeProcess, process_id)
        assert process.status == RunStatus.FINISHED
    assert any(record.exc_info for record in caplog.records)


def _add_turn(client: TestClient, session_id: int, text: str) -> int:
    """Add one more pending chat turn to an existing session and return its id."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        process = GenerativeProcess(session_id=session_id, status=RunStatus.NOT_STARTED)
        db.add(process)
        db.commit()
        db.refresh(process)
        db.add(
            ProcessData(
                process_id=process.id, is_input=True, data=text, data_type="str"
            )
        )
        db.commit()
        return process.id


def test_chat_turn_skips_cleanup_when_the_index_is_reused(
    client: TestClient, document_files: list[str], monkeypatch, chat_stub_llm
):
    """A turn that finds its index already built has nothing new to clean up."""
    session_id, first_turn = _chat_process(client, document_files, "reused")
    RAGJob(generative_process_id=first_turn).run()
    second_turn = _add_turn(client, session_id, "Tell me more about DashAI")
    calls: list[tuple[object, ...]] = []
    monkeypatch.setattr(
        rag_job_module,
        "run_post_index_cleanup",
        lambda *args: calls.append(args),
    )

    RAGJob(generative_process_id=second_turn).run()

    assert calls == []


def test_chat_turn_cleans_up_when_the_identity_changed_before_the_turn(
    client: TestClient, document_files: list[str], monkeypatch, chat_stub_llm
):
    """A turn that rebuilds a changed retriever cleans up around its live root."""
    session_id, first_turn = _chat_process(client, document_files, "rebuilt")
    RAGJob(generative_process_id=first_turn).run()
    _set_bm25_k1(client, session_id, NEW_K1)
    second_turn = _add_turn(client, session_id, "Tell me more about DashAI")
    events: list[tuple[str, object]] = []
    original_build_pipeline = SetupService.build_pipeline

    def build_pipeline(self, config):
        """Build the pipeline and record its root bridge id."""
        pipeline = original_build_pipeline(self, config)
        events.append(("build", pipeline.retriever.get_id()))
        return pipeline

    monkeypatch.setattr(SetupService, "build_pipeline", build_pipeline)
    monkeypatch.setattr(
        rag_job_module,
        "run_post_index_cleanup",
        lambda *args: events.append(("cleanup", args[2:])),
    )

    RAGJob(generative_process_id=second_turn).run()

    rag_path = client.app.container["config"]["RAG_PATH"]
    (build_kind, root_id), (cleanup_kind, cleanup_args) = events
    assert (build_kind, cleanup_kind) == ("build", "cleanup")
    assert cleanup_args == (session_id, root_id, rag_path)


def test_chat_turn_releases_the_index_it_replaced(
    client: TestClient, document_files: list[str], chat_stub_llm
):
    """After a rebuilding turn only the live sparse row of the session remains."""
    session_id, first_turn = _chat_process(client, document_files, "replaced")
    RAGJob(generative_process_id=first_turn).run()
    before = _sparse_rows_of(client, session_id)
    _set_bm25_k1(client, session_id, NEW_K1)
    second_turn = _add_turn(client, session_id, "Tell me more about DashAI")

    RAGJob(generative_process_id=second_turn).run()

    after = _sparse_rows_of(client, session_id)
    assert len(before) == 1, before
    assert len(after) == 1, after
    assert after[0][0] != before[0][0]
    assert not os.path.exists(before[0][1]), "the replaced folder must be released"


# ===================================================================
# Stale rows that a failed cleanup left behind
# ===================================================================


def _pipeline_id_of(db: Session, session_id: int) -> int:
    """Return the pipeline id of a session."""
    return db.query(RAGPipeline.id).filter_by(session_id=session_id).scalar()


def test_stale_row_probe_sees_leftovers_only(orm_db, tmp_path):
    """The probe is false for a clean index and true once a stale root or set exists."""
    session = _insert_rag_session(orm_db, f"probe_{uuid.uuid4().hex[:8]}")
    document = _insert_data_document(orm_db, tmp_path / "docs", "probe.txt", ["p"])
    index = _build_index(orm_db, tmp_path, session.id, document.id)
    assert cleanup_service.has_stale_index_rows(orm_db, session.id) is True

    _cleanup(orm_db, index)
    assert cleanup_service.has_stale_index_rows(orm_db, session.id) is False

    _chunk_set(orm_db, session.id, document.id, index.rag_path)
    orm_db.commit()
    assert cleanup_service.has_stale_index_rows(orm_db, session.id) is True


def test_stale_row_probe_is_false_for_a_session_without_rows(orm_db):
    """A session that never indexed has nothing to clean."""
    session = _insert_rag_session(orm_db, f"probe_empty_{uuid.uuid4().hex[:8]}")

    assert cleanup_service.has_stale_index_rows(orm_db, session.id) is False


def _add_leftover_root(client: TestClient, session_id: int) -> int:
    """Add a bridge no child link reaches, as a failed cleanup would leave it."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        bridge_id = _bare_bridge(db, _pipeline_id_of(db, session_id))
        db.commit()
        return bridge_id


def test_chat_turn_retries_leftover_stale_rows_once(
    client: TestClient, document_files: list[str], monkeypatch, chat_stub_llm
):
    """Stale rows left by an earlier failed cleanup are released by the next turn."""
    session_id, first_turn = _chat_process(client, document_files, "leftover")
    RAGJob(generative_process_id=first_turn).run()
    leftover = _add_leftover_root(client, session_id)
    calls: list[tuple[object, ...]] = []
    original_cleanup = rag_job_module.run_post_index_cleanup

    def record_cleanup(*args):
        """Count the call and run the real cleanup."""
        calls.append(args)
        original_cleanup(*args)

    monkeypatch.setattr(rag_job_module, "run_post_index_cleanup", record_cleanup)
    second_turn = _add_turn(client, session_id, "Tell me more about DashAI")

    RAGJob(generative_process_id=second_turn).run()

    assert len(calls) == 1
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        assert db.get(RAGRetriever, leftover) is None

    third_turn = _add_turn(client, session_id, "And one more question")
    RAGJob(generative_process_id=third_turn).run()

    assert len(calls) == 1, "a clean index must not trigger the cleanup again"
