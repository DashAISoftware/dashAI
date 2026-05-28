"""Factory for retriever instances with full lifecycle encapsulation.

Single-call ``create()`` interface encapsulates DB-record resolution,
persistence planning, constructor injection, and composite child recursion.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy.orm import Session

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
    """Result of retriever creation via RetrieverFactory."""

    db_record_id: int
    model: RetrieverModel


class RetrieverFactory:
    """Creates retriever instances with full persistence lifecycle.

    Handles sparse/dense unit retrievers and composite retrievers with
    recursive child construction. All DB access delegated to
    ``RetrieverRepository``.
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

    def create(
        self,
        component_name: str,
        params: Dict[str, Any],
    ) -> RetrieverFactoryResult:
        """Full lifecycle: resolve → construct → persist.

        Dispatches to ``_create_composite`` or ``_create_unit`` based
        on the resolved class.
        """
        model_class = self._registry[component_name]["class"]

        if issubclass(model_class, CompositeRetriever):
            return self._create_composite(model_class, params)

        return self._create_unit(model_class, params)

    # ── Composite ────────────────────────────────────────────────────

    def _create_composite(
        self,
        model_class: type[RetrieverModel],
        params: Dict[str, Any],
    ) -> RetrieverFactoryResult:
        existing = self._load_composite_from_db(model_class, params)
        if existing is not None:
            return RetrieverFactoryResult(
                db_record_id=existing.get_id(),
                model=existing,
            )

        children_configs: List[Dict[str, Any]] = params.pop("children")
        children_instances: List[RetrieverModel] = []
        for child_config in children_configs:
            children_instances.append(self._create_child_retriever(child_config))

        params["children"] = children_instances
        model = model_class(**params)
        bridge_record_id = self._save_composite(model)
        model.set_id(bridge_record_id)
        return RetrieverFactoryResult(
            db_record_id=bridge_record_id,
            model=model,
        )

    def _create_child_retriever(self, child_config: Dict[str, Any]) -> RetrieverModel:
        result = self.create(
            component_name=child_config["component"],
            params=child_config["params"],
        )
        return result.model

    def _load_composite_from_db(
        self,
        model_class: type[RetrieverModel],
        params: Dict[str, Any],
    ) -> RetrieverModel | None:
        class_name = model_class.__name__
        bridge_record = self._repo.find_composite(
            self._pipeline_id,
            class_name,
        )
        if bridge_record is None:
            return None

        child_links = self._repo.find_composite_children(bridge_record.id)
        if not child_links:
            return None

        children: List[RetrieverModel] = []
        for link in child_links:
            child_bridge = self._repo.get_bridge_by_id(link.child_id)
            if child_bridge is None:
                return None
            child_result = self.create(
                component_name=child_bridge.class_name,
                params={},
            )
            children.append(child_result.model)

        composite_params = {k: v for k, v in params.items() if k != "children"}
        model = model_class(children=children, **composite_params)
        model.set_id(bridge_record.id)
        return model

    def _save_composite(self, model: CompositeRetriever) -> int:
        child_ids: List[int] = []
        for child in model.get_children():
            cid = child.get_id()
            if cid is None:
                raise ValueError(f"Child {child.__class__.__name__} has no bridge ID.")
            child_ids.append(cid)
        bridge_record = self._repo.save_composite(
            model.__class__.__name__,
            self._pipeline_id,
            child_ids,
        )
        return bridge_record.id

    # ── Unit ─────────────────────────────────────────────────────────

    def _create_unit(
        self,
        model_class: type[RetrieverModel],
        params: Dict[str, Any],
    ) -> RetrieverFactoryResult:
        sorted_params = dict(sorted(params.items()))
        class_name = model_class.__name__

        self._inject_infra(params)

        loaded = self._load_unit_from_db(
            model_class,
            class_name,
            sorted_params,
        )
        if loaded is not None:
            return RetrieverFactoryResult(
                db_record_id=loaded.get_id(),
                model=loaded,
            )

        if issubclass(model_class, DenseRetriever):
            params["persistence"] = DensePersistence(
                matrix_dirs={}, embedding_model_id=0,
            )
        elif issubclass(model_class, SparseRetriever):
            params["persistence"] = SparsePersistence(model_dir=None)

        model = model_class(**params)
        bridge_record_id = self._save_unit(model, sorted_params)
        model.set_id(bridge_record_id)
        return RetrieverFactoryResult(
            db_record_id=bridge_record_id,
            model=model,
        )

    def _inject_infra(self, params: Dict[str, Any]) -> None:
        params["env_rag_path"] = self._env_rag_path
        params["chunks"] = self._chunks
        if "persistence" not in params:
            params["persistence"] = None

    def _load_unit_from_db(
        self,
        model_class: type[RetrieverModel],
        class_name: str,
        sorted_params: Dict[str, Any],
    ) -> RetrieverModel | None:
        if issubclass(model_class, DenseRetriever):
            return self._load_dense(class_name, sorted_params)
        if issubclass(model_class, SparseRetriever):
            return self._load_sparse(class_name, sorted_params)
        raise ValueError(f"Unsupported unit retriever: {model_class.__name__}")

    def _load_dense(
        self,
        class_name: str,
        sorted_params: Dict[str, Any],
    ) -> RetrieverModel | None:
        detail_record = self._repo.find_dense(
            class_name,
            sorted_params,
            self._chunk_set_id,
        )
        persistence = self._build_dense_persistence(detail_record)
        model_class = self._registry[class_name]["class"]

        if detail_record is not None:
            params = dict(sorted_params)
            params["chunks"] = self._chunks
            params["env_rag_path"] = self._env_rag_path
            params["persistence"] = persistence
            model = model_class(**params)
            bridge_record = self._repo.find_bridge_for_sub_table(
                detail_record,
                class_name,
            )
            if bridge_record is not None:
                model.set_id(bridge_record.id)
            return model

        return None

    def _load_sparse(
        self,
        class_name: str,
        sorted_params: Dict[str, Any],
    ) -> RetrieverModel | None:
        detail_record = self._repo.find_sparse(
            class_name,
            sorted_params,
            self._chunk_set_id,
        )
        persistence = self._build_sparse_persistence(detail_record)
        model_class = self._registry[class_name]["class"]

        if detail_record is not None:
            params = dict(sorted_params)
            params["chunks"] = self._chunks
            params["env_rag_path"] = self._env_rag_path
            params["persistence"] = persistence
            model = model_class(**params)
            bridge_record = self._repo.find_bridge_for_sub_table(
                detail_record,
                class_name,
            )
            if bridge_record is not None:
                model.set_id(bridge_record.id)
            return model

        return None

    def _build_sparse_persistence(
        self,
        detail_record,
    ) -> SparsePersistence:
        if detail_record is None:
            return SparsePersistence(model_dir=None)
        return SparsePersistence(model_dir=detail_record.storage_folder)

    def _build_dense_persistence(
        self,
        detail_record,
    ) -> DensePersistence:
        encoding_params = self._extract_encoding_from_detail(detail_record)
        if encoding_params is None:
            emb_record_id = 0
        else:
            emb_record = self._repo.find_or_create_embedding_model(
                encoding_params["class"],
                encoding_params["params"],
            )
            emb_record_id = emb_record.id

        existing_matrices = self._repo.find_embedding_matrices(
            list(self._chunks.keys()),
            self._chunk_set_id,
            emb_record_id,
        )
        matrix_dirs: Dict[int, str] = {}
        for doc_id in list(self._chunks.keys()):
            existing = existing_matrices.get(doc_id)
            if existing is not None:
                matrix_dirs[doc_id] = existing.storage_folder
            else:
                folder_name = (
                    f"doc_id-{doc_id}__"
                    f"chunk_set_id-{self._chunk_set_id}__"
                    f"embedding_model_id-{emb_record_id}"
                )
                matrix_dirs[doc_id] = os.path.join(
                    self._env_rag_path,
                    "embeddings",
                    folder_name,
                )
        return DensePersistence(
            matrix_dirs=matrix_dirs,
            embedding_model_id=emb_record_id,
        )

    def _extract_encoding_from_detail(
        self,
        detail_record,
    ) -> Dict[str, Any] | None:
        if detail_record is None:
            return None
        params = detail_record.parameters or {}
        encoding = params.get("encoding_model", {})
        properties = encoding.get("properties", {})
        inner_params = properties.get("params", {})
        comp = inner_params.get("comp", {})
        return {
            "class": comp.get("component"),
            "params": comp.get("params", {}),
        }

    def _save_unit(self, model: RetrieverModel, sorted_params: Dict[str, Any]) -> int:
        if isinstance(model, DenseRetriever):
            return self._save_dense(model, sorted_params)
        if isinstance(model, SparseRetriever):
            return self._save_sparse(model, sorted_params)
        raise ValueError(f"Unsupported retriever: {type(model).__name__}")

    def _save_dense(self, model: DenseRetriever, sorted_params: Dict[str, Any]) -> int:
        import numpy as np

        for doc_id, matrix_dir in model._persistence.matrix_dirs.items():
            matrix_path = os.path.join(matrix_dir, "embeddings.npy")
            if not os.path.exists(matrix_path):
                continue
            existing = self._repo.find_embedding_matrix(
                doc_id,
                self._chunk_set_id,
                model._persistence.embedding_model_id,
            )
            if existing is not None:
                continue
            loaded = np.load(matrix_path)
            self._repo.save_embedding_matrix(
                doc_id,
                self._chunk_set_id,
                model._persistence.embedding_model_id,
                matrix_dir,
                list(loaded.shape),
            )

        bridge_record = self._repo.create_bridge(
            model.__class__.__name__,
            self._pipeline_id,
        )
        self._repo.save_dense(
            model.__class__.__name__,
            sorted_params,
            bridge_record.id,
            self._chunk_set_id,
            model._persistence.embedding_model_id,
        )
        return bridge_record.id

    def _save_sparse(self, model: SparseRetriever, sorted_params: Dict[str, Any]) -> int:
        folder_id = uuid4().hex
        storage_folder = os.path.join(
            self._env_rag_path,
            "sparse_retrievers",
            f"sparse_retriever_id-{folder_id}",
        )
        model._persistence.model_dir = storage_folder
        model.save()

        bridge_record = self._repo.create_bridge(
            model.__class__.__name__,
            self._pipeline_id,
        )
        self._repo.save_sparse(
            model.__class__.__name__,
            sorted_params,
            storage_folder,
            bridge_record.id,
            self._chunk_set_id,
        )
        return bridge_record.id
