"""Factory for retriever instances with full lifecycle encapsulation.

Single-call ``create()`` interface encapsulates DB-record resolution,
persistence planning, constructor injection, and composite child recursion.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

from DashAI.back.core.schema_fields.utils import fill_objects, normalize_payload
from DashAI.back.dependencies.registry.component_registry import ComponentRegistry
from DashAI.back.models.RAG.documents.chunk import Chunk
from DashAI.back.models.RAG.retrievers.composite.composite_retriever import (
    CompositeRetriever,
)
from DashAI.back.models.RAG.retrievers.dense.dense_retriever import DenseRetriever
from DashAI.back.models.RAG.retrievers.persistence import (
    DensePersistence,
    SparsePersistence,
)
from DashAI.back.models.RAG.retrievers.retriever_model import RetrieverModel
from DashAI.back.models.RAG.retrievers.retriever_repository import (
    RetrieverRepository,
)
from DashAI.back.models.RAG.retrievers.sparse.sparse_retriever import SparseRetriever


@dataclass(frozen=True)
class RetrieverFactoryResult:
    db_record_id: int
    model: RetrieverModel


class RetrieverFactory:
    """Creates retriever instances with full persistence lifecycle.

    All DB access delegated to ``RetrieverRepository``.
    """

    def __init__(
        self,
        db: Session,
        pipeline_id: int,
        registry: ComponentRegistry,
        env_rag_path: str,
        chunks: Dict[int, Dict[int, Chunk]],
        chunk_set_id: int,
    ):
        self._db = db
        self._pipeline_id = pipeline_id
        self._registry = registry
        self._env_rag_path = env_rag_path
        self._chunks = chunks
        self._chunk_set_id = chunk_set_id
        self._repo = RetrieverRepository(db)

    # ── Public entry point ───────────────────────────────────────────

    def create(
        self,
        component_name: str,
        params: Dict[str, Any],
    ) -> RetrieverFactoryResult:
        params = normalize_payload(params)
        model_class = self._registry[component_name]["class"]

        if issubclass(model_class, CompositeRetriever):
            return self._create_composite(model_class, params)

        return self._create_unit(model_class, params)

    # ── Composite ────────────────────────────────────────────────────

    def _create_composite(self, model_class, params):
        existing = self._load_composite_from_db(model_class, params)
        if existing is not None:
            return RetrieverFactoryResult(
                db_record_id=existing.get_id(), model=existing,
            )

        children_configs = params.pop("children")
        children_instances = [
            self._create_child_retriever(c) for c in children_configs
        ]
        params["children"] = children_instances
        model = model_class(**params)
        bridge_id = self._save_composite(model)
        model.set_id(bridge_id)
        return RetrieverFactoryResult(db_record_id=bridge_id, model=model)

    def _create_child_retriever(self, child_config):
        return self.create(
            component_name=child_config["component"],
            params=child_config["params"],
        ).model

    def _load_composite_from_db(self, model_class, params):
        bridge_record = self._repo.find_composite(
            self._pipeline_id, model_class.__name__,
        )
        if bridge_record is None:
            return None
        child_links = self._repo.find_composite_children(bridge_record.id)
        if not child_links:
            return None

        children = []
        for link in child_links:
            child_bridge = self._repo.get_bridge_by_id(link.child_id)
            if child_bridge is None:
                return None
            child_params = self._load_child_params(child_bridge.id, child_bridge.class_name)
            if child_params is None:
                return None
            children.append(
                self.create(
                    component_name=child_bridge.class_name,
                    params=child_params,
                ).model,
            )

        model = model_class(
            children=children,
            **{k: v for k, v in params.items() if k != "children"},
        )
        model.set_id(bridge_record.id)
        return model

    def _load_child_params(
        self, bridge_id: int, class_name: str,
    ) -> Dict[str, Any] | None:
        sparse = self._repo.find_sparse_by_bridge_id(bridge_id)
        if sparse is not None and sparse.parameters is not None:
            return dict(sorted(sparse.parameters.items()))
        dense = self._repo.find_dense_by_bridge_id(bridge_id)
        if dense is not None and dense.parameters is not None:
            return dict(sorted(dense.parameters.items()))
        return None

    def _save_composite(self, model):
        child_ids = []
        for child in model.get_children():
            cid = child.get_id()
            if cid is None:
                raise ValueError(f"Child {child.__class__.__name__} has no bridge ID.")
            child_ids.append(cid)
        return self._repo.save_composite(
            model.__class__.__name__, self._pipeline_id, child_ids,
        ).id

    # ── Unit ─────────────────────────────────────────────────────────

    def _create_unit(self, model_class, params):
        sorted_params = dict(sorted(params.items()))

        loaded = self._load_unit_from_db(
            model_class, model_class.__name__, sorted_params,
        )
        if loaded is not None:
            return RetrieverFactoryResult(
                db_record_id=loaded.get_id(), model=loaded,
            )

        validated = model_class.SCHEMA.model_validate(params)
        resolved = fill_objects(validated, self._registry)
        model = model_class(**resolved)

        if issubclass(model_class, DenseRetriever):
            model.inject_infra(
                self._env_rag_path, self._chunks,
                DensePersistence(matrix_dirs={}, embedding_model_id=0),
            )
            model.init_model()
            self._finalize_dense(model, sorted_params)
        elif issubclass(model_class, SparseRetriever):
            model.inject_infra(
                self._env_rag_path, self._chunks,
                SparsePersistence(model_dir=None),
            )
            model.init_model()
        else:
            raise ValueError(
                f"Unsupported unit retriever: {model_class.__name__}"
            )

        bridge_id = self._save_unit(model, sorted_params)
        model.set_id(bridge_id)
        return RetrieverFactoryResult(db_record_id=bridge_id, model=model)

    def _finalize_dense(self, model, sorted_params):
        """After init_model() for a new dense model: persist embedding
        model, build persistence with the proper ID, compute matrices."""
        enc = model.params.get("encoding_model")
        if not enc:
            return
        emb_record = self._repo.find_or_create_embedding_model(
            enc["class_name"],
            dict(sorted(enc["parameters"].items())),
        )
        model._persistence = self._dense_persistence(emb_record.id)
        model.compute_missing_embeddings()
        model.init_similarity_matrix()

    def _dense_persistence(self, embedding_model_id: int) -> DensePersistence:
        """Build a DensePersistence with matrix dirs for every known doc."""
        matrix_dirs = {}
        for doc_id in self._chunks:
            folder = (
                f"doc_id-{doc_id}__"
                f"chunk_set_id-{self._chunk_set_id}__"
                f"embedding_model_id-{embedding_model_id}"
            )
            matrix_dirs[doc_id] = os.path.join(
                self._env_rag_path, "embeddings", folder,
            )
        return DensePersistence(
            matrix_dirs=matrix_dirs,
            embedding_model_id=embedding_model_id,
        )

    def _load_unit_from_db(self, model_class, class_name, sorted_params):
        if issubclass(model_class, DenseRetriever):
            return self._load_dense(class_name, sorted_params)
        if issubclass(model_class, SparseRetriever):
            return self._load_sparse(class_name, sorted_params)
        raise ValueError(f"Unsupported unit retriever: {model_class.__name__}")

    def _load_dense(self, class_name, sorted_params):
        record = self._repo.find_dense(class_name, sorted_params, self._chunk_set_id)
        if record is None:
            return None
        persistence = self._dense_persistence(record.embedding_model_id)
        model_class = self._registry[class_name]["class"]

        validated = model_class.SCHEMA.model_validate(dict(sorted_params))
        resolved = fill_objects(validated, self._registry)
        model = model_class(**resolved)
        model.inject_infra(self._env_rag_path, self._chunks, persistence)
        model.init_model()
        bridge = self._repo.find_bridge_for_sub_table(record, class_name)
        if bridge is not None:
            model.set_id(bridge.id)
        return model

    def _load_sparse(self, class_name, sorted_params):
        record = self._repo.find_sparse(class_name, sorted_params, self._chunk_set_id)
        if record is None:
            return None
        persistence = SparsePersistence(model_dir=record.storage_folder)
        model_class = self._registry[class_name]["class"]

        validated = model_class.SCHEMA.model_validate(dict(sorted_params))
        resolved = fill_objects(validated, self._registry)
        model = model_class(**resolved)
        model.inject_infra(self._env_rag_path, self._chunks, persistence)
        model.init_model()
        bridge = self._repo.find_bridge_for_sub_table(record, class_name)
        if bridge is not None:
            model.set_id(bridge.id)
        return model

    # ── Save ─────────────────────────────────────────────────────────

    def _save_unit(self, model, sorted_params):
        if isinstance(model, DenseRetriever):
            return self._save_dense(model, sorted_params)
        if isinstance(model, SparseRetriever):
            return self._save_sparse(model, sorted_params)
        raise ValueError(f"Unsupported retriever: {type(model).__name__}")

    def _save_dense(self, model, sorted_params):
        import numpy as np

        for doc_id, mdir in model._persistence.matrix_dirs.items():
            path = os.path.join(mdir, "embeddings.npy")
            if not os.path.exists(path):
                continue
            if self._repo.find_embedding_matrix(
                doc_id, self._chunk_set_id, model._persistence.embedding_model_id,
            ):
                continue
            self._repo.save_embedding_matrix(
                doc_id, self._chunk_set_id,
                model._persistence.embedding_model_id,
                mdir, list(np.load(path).shape),
            )

        bridge = self._repo.create_bridge(
            model.__class__.__name__, self._pipeline_id,
        )
        self._repo.save_dense(
            model.__class__.__name__, sorted_params,
            bridge.id, self._chunk_set_id,
            model._persistence.embedding_model_id,
        )
        return bridge.id

    def _save_sparse(self, model, sorted_params):
        folder_id = uuid4().hex
        storage_folder = os.path.join(
            self._env_rag_path, "sparse_retrievers",
            f"sparse_retriever_id-{folder_id}",
        )
        model._persistence.model_dir = storage_folder
        model.save()
        bridge = self._repo.create_bridge(
            model.__class__.__name__, self._pipeline_id,
        )
        self._repo.save_sparse(
            model.__class__.__name__, sorted_params,
            storage_folder, bridge.id, self._chunk_set_id,
        )
        return bridge.id
