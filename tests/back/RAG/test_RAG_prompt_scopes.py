"""Prompt scopes, class-aware hashing and fork lineage.

Covers the Phase 1 prompt-catalog contract: the row hash includes the prompt
class, defaults are immutable, editing a default forks it, drafts are promoted
on save, and deleting a prompt detaches pipelines instead of removing them.
"""

import uuid

import pytest

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPipeline,
    RAGPrompt,
    RAGSessionPrompt,
)
from DashAI.back.services.RAG.exceptions import RAGPromptValidationError
from DashAI.back.services.RAG.prompt_service import (
    PromptConflictError,
    PromptService,
)
from DashAI.back.services.RAG.utils import build_prompt_hash


def _template() -> str:
    """Return a unique template valid for the generation prompt classes."""
    return f"Use {{chunks}} to answer {{input}} {uuid.uuid4().hex}"


def _registry(client):
    return client.app.container["component_registry"]


def _service(client, db) -> PromptService:
    return PromptService(db, _registry(client))


class _NoopSessionService:
    """Session service stub that records calls and drops the prompt links."""

    def __init__(self, db=None) -> None:
        self.db = db
        self.deleted: list[int] = []

    def delete_session(self, session_id: int, commit: bool = False) -> None:
        self.deleted.append(session_id)
        if self.db is not None:
            self.db.query(RAGSessionPrompt).filter_by(session_id=session_id).delete()


def test_hash_includes_the_prompt_class(client):
    """Identical parameters under two prompt classes get distinct hashes."""
    params = {"template": _template()}
    generation_hash = build_prompt_hash("CustomRAGGenerationPrompt", params)
    rewriting_hash = build_prompt_hash("CustomQueryRewritingPrompt", params)
    assert generation_hash != rewriting_hash

    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        first = service.get_or_create("CustomRAGGenerationPrompt", "first", params)
        second = service.get_or_create("CustomQueryRewritingPrompt", "second", params)
        assert first.id != second.id
        hashes = {
            row[0]
            for row in db.query(RAGPrompt.parameters_hash)
            .filter(RAGPrompt.id.in_([first.id, second.id]))
            .all()
        }
    assert hashes == {generation_hash, rewriting_hash}


def test_defaults_are_seeded_and_immutable(client):
    """Seeded defaults carry the flag and reject edits and deletes."""
    session_factory = client.app.container["session_factory"]
    default_id = None
    with session_factory() as db:
        service = _service(client, db)
        library = service.get_library()
        defaults = [prompt for prompt in library if prompt.is_default]
        assert defaults, "Expected the built-in prompts to be seeded"
        default = next(
            prompt
            for prompt in defaults
            if prompt.class_name == "DefaultRAGGenerationPrompt"
        )
        default_id = default.id
        assert default.is_library is False
        assert default.origin == "default"

        with pytest.raises(RAGPromptValidationError):
            service.update_library_prompt(default_id, name="renamed")
        with pytest.raises(RAGPromptValidationError):
            service.delete(default_id)

    with session_factory() as db:
        row = db.get(RAGPrompt, default_id)
        assert row is not None
        assert row.is_default is True
        assert row.is_library is False


def test_seeding_copies_the_component_templates_map(client):
    """A seeded row must not share its templates dict with the class metadata."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        service.get_library()
        default = (
            db.query(RAGPrompt)
            .filter(
                RAGPrompt.class_name == "DefaultRAGGenerationPrompt",
                RAGPrompt.is_default.is_(True),
            )
            .first()
        )
        assert default is not None
        component_templates = _registry(client)["DefaultRAGGenerationPrompt"][
            "class"
        ].metadata["templates"]
        expected = dict(component_templates)

        default.parameters["templates"]["en"] = "mutated {input} {chunks}"

        assert component_templates == expected
        db.rollback()


def test_forking_a_default_creates_a_custom_library_row(client):
    """Editing a default forks it; the default row stays untouched."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        service.get_library()
        default = (
            db.query(RAGPrompt)
            .filter(
                RAGPrompt.class_name == "DefaultRAGGenerationPrompt",
                RAGPrompt.is_default.is_(True),
            )
            .one()
        )
        default_id = default.id
        original_parameters = dict(default.parameters)
        original_hash = default.parameters_hash
        expected_template = original_parameters["templates"][
            original_parameters.get("language", "en")
        ]

        forked = service.fork_prompt(default_id, "My generation prompt")

        assert forked.id != default_id
        assert forked.class_name == "CustomRAGGenerationPrompt"
        assert forked.is_library is True
        assert forked.is_default is False
        assert forked.origin == "library"
        assert forked.based_on_id == default_id
        assert forked.parameters == {"template": expected_template}

    with session_factory() as db:
        row = db.get(RAGPrompt, default_id)
        assert row is not None
        assert row.is_default is True
        assert row.parameters == original_parameters
        assert row.parameters_hash == original_hash


def test_forking_a_library_prompt_does_not_point_at_itself(client):
    """Re-forking the same library content returns it without self-lineage."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        library = service.create(
            "CustomRAGGenerationPrompt", "same name", {"template": _template()}
        )

        same = service.fork_prompt(library.id, library.name)
        assert same.id == library.id
        assert db.get(RAGPrompt, library.id).based_on_id is None

        with pytest.raises(PromptConflictError):
            service.fork_prompt(library.id, "a different name")


def test_create_promotes_a_matching_draft(client):
    """Saving content that already exists as a draft promotes that row."""
    template = _template()
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        draft = service.get_or_create(
            "CustomRAGGenerationPrompt", "pipeline_1_X", {"template": template}
        )
        assert draft.is_library is False
        assert draft.origin == "draft"

        created = service.create(
            "CustomRAGGenerationPrompt", "Saved prompt", {"template": template}
        )
        assert created.id == draft.id
        assert created.is_library is True
        assert created.is_default is False
        assert created.origin == "library"
        assert created.name == "Saved prompt"

    with session_factory() as db:
        prompt_hash = build_prompt_hash(
            "CustomRAGGenerationPrompt", {"template": template}
        )
        assert (
            db.query(RAGPrompt).filter(RAGPrompt.parameters_hash == prompt_hash).count()
            == 1
        )


def test_update_library_prompt_edits_in_place(client):
    """A library prompt is edited in place and collisions/defaults reject."""
    first_template = _template()
    second_template = _template()
    third_template = _template()
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        first = service.create(
            "CustomRAGGenerationPrompt", "first", {"template": first_template}
        )
        second = service.create(
            "CustomRAGGenerationPrompt", "second", {"template": second_template}
        )

        updated = service.update_library_prompt(
            first.id,
            name="first renamed",
            parameters={"template": third_template},
        )
        assert updated.id == first.id
        assert updated.name == "first renamed"
        assert updated.parameters == {"template": third_template}

        with pytest.raises(RAGPromptValidationError):
            service.update_library_prompt(
                first.id, parameters={"template": second_template}
            )

        default = db.query(RAGPrompt).filter(RAGPrompt.is_default.is_(True)).first()
        assert default is not None
        with pytest.raises(RAGPromptValidationError):
            service.update_library_prompt(default.id, name="nope")

    with session_factory() as db:
        row = db.get(RAGPrompt, first.id)
        assert row is not None
        assert row.parameters == {"template": third_template}
        assert row.parameters_hash == build_prompt_hash(
            "CustomRAGGenerationPrompt", {"template": third_template}
        )
        assert db.get(RAGPrompt, second.id) is not None


def test_delete_detaches_pipelines_instead_of_deleting_them(client):
    """Deleting a prompt nulls the pipeline snapshot instead of dropping it."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        prompt = service.create(
            "CustomRAGGenerationPrompt", "to delete", {"template": _template()}
        )
        prompt_id = prompt.id

        session = GenerativeSession(
            name=f"scope_session_{uuid.uuid4().hex[:8]}",
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        pipeline = RAGPipeline(
            session_id=session.id,
            name="",
            description=None,
            parameters=None,
            prompt_id=prompt_id,
        )
        db.add(pipeline)
        db.add(
            RAGSessionPrompt(
                session_id=session.id,
                slot_path="generation",
                prompt_id=prompt_id,
            )
        )
        db.commit()
        db.refresh(pipeline)
        pipeline_id = pipeline.id
        session_id = session.id

        session_service = _NoopSessionService(db)
        service.delete(
            prompt_id,
            cascade_sessions=True,
            session_service=session_service,
        )

        assert session_service.deleted == [session_id]
        assert db.get(RAGPrompt, prompt_id) is None
        db.expire_all()
        remaining = db.get(RAGPipeline, pipeline_id)
        assert remaining is not None
        assert remaining.prompt_id is None
        assert remaining.session_id == session_id


def test_delete_with_detach_repoints_pipelines_to_the_draft(client):
    """Detach keeps the build history pointing at the equivalent draft."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        prompt = service.create(
            "CustomRAGGenerationPrompt", "detached pipeline", {"template": _template()}
        )
        prompt_id = prompt.id
        session = GenerativeSession(
            name=f"detach_pipeline_{uuid.uuid4().hex[:8]}",
            task_name="RAGTask",
            model_name="RAGPipeline",
            parameters={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        pipeline = RAGPipeline(
            session_id=session.id,
            name="",
            description=None,
            parameters=None,
            prompt_id=prompt_id,
        )
        db.add(pipeline)
        db.add(
            RAGSessionPrompt(
                session_id=session.id,
                slot_path="generation",
                prompt_id=prompt_id,
            )
        )
        db.commit()
        pipeline_id = pipeline.id
        session_id = session.id

        service.delete(prompt_id, detach=True)

        binding = db.get(RAGSessionPrompt, (session_id, "generation"))
        draft_id = binding.prompt_id
        db.expire_all()
        remaining = db.get(RAGPipeline, pipeline_id)
        assert draft_id != prompt_id
        assert remaining is not None
        assert remaining.prompt_id == draft_id

    with session_factory() as db:
        assert db.get(RAGPrompt, prompt_id) is None
        assert db.get(RAGPrompt, draft_id) is not None
        assert db.get(RAGPipeline, pipeline_id).prompt_id == draft_id


def test_delete_removes_orphan_session_bindings(client):
    """A binding whose session row is gone must not survive the prompt."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        prompt = service.create(
            "CustomRAGGenerationPrompt", "orphan binding", {"template": _template()}
        )
        prompt_id = prompt.id
        # SQLite does not enforce the session FK in this database, so the row
        # can point at a session that was deleted without its bindings.
        db.add(
            RAGSessionPrompt(
                session_id=987654,
                slot_path="generation",
                prompt_id=prompt_id,
            )
        )
        db.commit()

        service.delete(prompt_id)

        assert (
            db.query(RAGSessionPrompt)
            .filter(RAGSessionPrompt.prompt_id == prompt_id)
            .count()
            == 0
        )

    with session_factory() as db:
        assert db.get(RAGPrompt, prompt_id) is None


def test_forking_a_legacy_default_draft_uses_the_custom_class(client):
    """A demoted ``Default*`` row must fork into its ``CUSTOM_CLASS`` counterpart."""
    template = _template()
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        legacy = RAGPrompt(
            class_name="DefaultRAGGenerationPrompt",
            name="legacy demoted default",
            parameters={"template": template},
            parameters_hash=build_prompt_hash(
                "DefaultRAGGenerationPrompt", {"template": template}
            ),
            is_library=False,
            is_default=False,
        )
        db.add(legacy)
        db.commit()
        legacy_id = legacy.id

        forked = service.fork_prompt(legacy_id, "forked legacy default")

        assert forked.class_name == "CustomRAGGenerationPrompt"
        assert forked.is_library is True
        assert forked.is_default is False
        assert forked.parameters == {"template": template}
