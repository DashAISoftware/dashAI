"""Session prompt slots and their bindings.

Covers Phase 2A of the prompt redesign: slot discovery, split/inject of the
prompt references stored in a session configuration, default/library/draft
binding semantics, language selection and detaching bindings before a library
row is deleted.
"""

import uuid

import pytest

from DashAI.back.dependencies.database.models import (
    GenerativeSession,
    RAGPrompt,
    RAGSessionPrompt,
)
from DashAI.back.models.RAG.prompts.evaluation.agentic_reranker_prompt import (
    AgenticRerankerPrompt,
)
from DashAI.back.models.RAG.prompts.evaluation.agentic_retriever_prompt import (
    AgenticRetrieverPrompt,
)
from DashAI.back.models.RAG.prompts.generation.RAG_generation_prompt import (
    RAGGenerationPrompt,
)
from DashAI.back.models.RAG.prompts.transformation.transformation_prompt import (
    QueryTransformationPrompt,
)
from DashAI.back.services.RAG.exceptions import RAGPromptValidationError
from DashAI.back.services.RAG.prompt_service import PromptService
from DashAI.back.services.RAG.utils import build_prompt_hash


def _service(client, db) -> PromptService:
    return PromptService(db, client.app.container["component_registry"])


def _template(placeholders: str, prefix: str = "prompt") -> str:
    return f"{placeholders} {prefix}_{uuid.uuid4().hex}"


def _create_session(db, name: str = None) -> GenerativeSession:
    session = GenerativeSession(
        name=name or f"binding_{uuid.uuid4().hex[:8]}",
        task_name="RAGTask",
        model_name="RAGPipeline",
        parameters={"documents": []},
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _nested_parameters() -> dict:
    return {
        "documents": [],
        "prompt": {
            "component": "CustomRAGGenerationPrompt",
            "params": {"template": _template("{chunks} {input}", "generation")},
        },
        "query_transformation": {
            "component": "LLMQueryRewriter",
            "params": {
                "prompt": {
                    "component": "CustomQueryRewritingPrompt",
                    "params": {"template": _template("{input} {history}", "rewriting")},
                }
            },
        },
        "retriever_model": {
            "component": "AgenticSingleRetriever",
            "params": {
                "prompt": {
                    "component": "CustomAgenticRetrieverPrompt",
                    "params": {
                        "template": _template("{input} {chunks}", "sufficiency")
                    },
                },
                "children": [
                    {
                        "component": "AgenticRerankerRetriever",
                        "params": {
                            "prompt": {
                                "component": "CustomAgenticRerankerPrompt",
                                "params": {
                                    "template": _template("{input} {chunks}", "filter")
                                },
                            }
                        },
                    }
                ],
            },
        },
    }


def test_discover_prompt_slots_for_every_prompt_family(client):
    """Generation, transformation, retriever and nested child slots are found."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        slots = service.discover_prompt_slots(_nested_parameters())

    by_path = {slot.slot_path: slot for slot in slots}
    assert list(by_path) == [
        "generation",
        "query_transformation.prompt",
        "retriever_model.children[0].prompt",
        "retriever_model.prompt",
    ]

    generation = by_path["generation"]
    assert generation.container is None
    assert generation.key is None
    assert generation.expected_base is RAGGenerationPrompt
    assert generation.default_component is None

    transformation = by_path["query_transformation.prompt"]
    assert transformation.expected_base is QueryTransformationPrompt
    assert transformation.default_component == "DefaultQueryRewritingPrompt"
    assert (
        transformation.container["prompt"]["component"] == "CustomQueryRewritingPrompt"
    )

    sufficiency = by_path["retriever_model.prompt"]
    assert sufficiency.expected_base is AgenticRetrieverPrompt
    assert sufficiency.default_component == "DefaultAgenticRetrieverPrompt"
    assert (
        sufficiency.container["prompt"]["component"] == "CustomAgenticRetrieverPrompt"
    )

    child = by_path["retriever_model.children[0].prompt"]
    assert child.expected_base is AgenticRerankerPrompt
    assert child.default_component == "DefaultAgenticRerankerPrompt"
    assert child.container["prompt"]["component"] == "CustomAgenticRerankerPrompt"


def test_split_and_inject_restore_the_same_prompt_contents(client):
    """Prompts are removed from parameters and injected back unchanged."""
    parameters = _nested_parameters()
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        clean, prompt_inputs = service.split_prompts(parameters)

        assert set(prompt_inputs) == {
            "generation",
            "query_transformation.prompt",
            "retriever_model.children[0].prompt",
            "retriever_model.prompt",
        }
        assert "prompt" not in clean
        assert "prompt" not in clean["query_transformation"]["params"]
        assert "prompt" not in clean["retriever_model"]["params"]
        assert (
            "prompt" not in clean["retriever_model"]["params"]["children"][0]["params"]
        )

        session = _create_session(db)
        service.sync_session_bindings(session.id, clean, prompt_inputs)
        db.commit()

        restored = service.inject_prompt_slots(session.id, clean)

    assert restored == parameters


def test_library_edit_is_shared_and_session_edit_creates_a_draft(client):
    """Two sessions see library edits; one session edit only changes its draft."""
    first_template = _template("{chunks} {input}", "first")
    second_template = _template("{chunks} {input}", "second")
    third_template = _template("{chunks} {input}", "third")
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        library = service.create(
            "CustomRAGGenerationPrompt", "shared", {"template": first_template}
        )
        first_session = _create_session(db)
        second_session = _create_session(db)
        prompt_inputs = {"generation": {"prompt_id": library.id}}

        service.sync_session_bindings(first_session.id, {}, prompt_inputs)
        service.sync_session_bindings(second_session.id, {}, prompt_inputs)
        db.commit()

        service.update_library_prompt(
            library.id, parameters={"template": second_template}
        )

        first = service.inject_prompt_slots(first_session.id, {})
        second = service.inject_prompt_slots(second_session.id, {})
        assert first["prompt"]["params"]["template"] == second_template
        assert second["prompt"]["params"]["template"] == second_template

        service.sync_session_bindings(
            first_session.id,
            {},
            {
                "generation": {
                    "prompt_id": library.id,
                    "params": {"template": third_template},
                }
            },
        )
        db.commit()

        first_edit = service.inject_prompt_slots(first_session.id, {})
        second_after = service.inject_prompt_slots(second_session.id, {})
        first_binding = db.get(RAGSessionPrompt, (first_session.id, "generation"))
        second_binding = db.get(RAGSessionPrompt, (second_session.id, "generation"))
        draft = db.get(RAGPrompt, first_binding.prompt_id)

        assert first_edit["prompt"]["params"]["template"] == third_template
        assert second_after["prompt"]["params"]["template"] == second_template
        assert first_binding.prompt_id != library.id
        assert second_binding.prompt_id == library.id
        assert draft.is_library is False
        assert draft.is_default is False


def test_editing_a_default_in_a_session_creates_a_custom_draft(client):
    """A session edit of a default produces a Custom* draft with lineage."""
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
        original_parameters = dict(default.parameters)
        template = _template("{chunks} {input}", "custom")

        session = _create_session(db)
        service.sync_session_bindings(
            session.id,
            {},
            {"generation": {"prompt_id": default.id, "params": {"template": template}}},
        )
        db.commit()

        binding = db.get(RAGSessionPrompt, (session.id, "generation"))
        draft = db.get(RAGPrompt, binding.prompt_id)
        db.expire_all()
        stored_default = db.get(RAGPrompt, default.id)

        assert draft.class_name == "CustomRAGGenerationPrompt"
        assert draft.is_library is False
        assert draft.is_default is False
        assert draft.based_on_id == default.id
        assert draft.parameters == {"template": template}
        assert stored_default.parameters == original_parameters


def test_a_spanish_default_language_is_preserved(client):
    """Binding a default keeps the selected language on the link."""
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

        by_id = _create_session(db)
        service.sync_session_bindings(
            by_id.id,
            {},
            {"generation": {"prompt_id": default.id, "language": "es"}},
        )
        by_component = _create_session(db)
        service.sync_session_bindings(
            by_component.id,
            {},
            {
                "generation": {
                    "component": "DefaultRAGGenerationPrompt",
                    "params": {"language": "es"},
                }
            },
        )
        db.commit()

        by_id_binding = db.get(RAGSessionPrompt, (by_id.id, "generation"))
        by_component_binding = db.get(RAGSessionPrompt, (by_component.id, "generation"))
        injected = service.inject_prompt_slots(by_id.id, {})
        injected_component = service.inject_prompt_slots(by_component.id, {})

    expected_template = default.parameters["templates"]["es"]
    assert by_id_binding.language == "es"
    assert by_component_binding.language == "es"
    assert injected["prompt"] == {
        "component": "DefaultRAGGenerationPrompt",
        "params": {"template": expected_template, "language": "es"},
    }
    assert injected_component["prompt"] == injected["prompt"]


def test_a_session_can_resave_its_own_draft_but_not_another_sessions(client):
    """Drafts are session-local: only the owning session may bind them again."""
    template = _template("{chunks} {input}", "owned_draft")
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        owner = _create_session(db)
        other = _create_session(db)

        service.sync_session_bindings(
            owner.id,
            {},
            {
                "generation": {
                    "component": "CustomRAGGenerationPrompt",
                    "params": {"template": template},
                }
            },
        )
        db.commit()
        draft_id = db.get(RAGSessionPrompt, (owner.id, "generation")).prompt_id
        assert db.get(RAGPrompt, draft_id).is_library is False

        # Re-saving the same draft is allowed: the slot already points at it.
        service.sync_session_bindings(
            owner.id,
            {},
            {"generation": {"prompt_id": draft_id}},
        )
        db.commit()
        assert db.get(RAGSessionPrompt, (owner.id, "generation")).prompt_id == draft_id

        # Another session cannot adopt it through its id.
        with pytest.raises(RAGPromptValidationError):
            service.sync_session_bindings(
                other.id,
                {},
                {"generation": {"prompt_id": draft_id}},
            )
        db.rollback()


def test_a_legacy_default_row_with_only_a_template_still_reads(client):
    """A default row whose parameters only store a template is readable."""
    template = _template("{chunks} {input}", "legacy_default")
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        parameters = {"template": template}
        prompt = RAGPrompt(
            class_name="DefaultRAGGenerationPrompt",
            name="legacy default",
            parameters=parameters,
            parameters_hash=build_prompt_hash("DefaultRAGGenerationPrompt", parameters),
            is_library=False,
            is_default=True,
        )
        db.add(prompt)
        db.flush()
        session = _create_session(db)
        db.add(
            RAGSessionPrompt(
                session_id=session.id,
                slot_path="generation",
                prompt_id=prompt.id,
            )
        )
        db.commit()

        injected = service.inject_prompt_slots(session.id, {})

    assert injected["prompt"]["component"] == "DefaultRAGGenerationPrompt"
    assert injected["prompt"]["params"]["template"] == template


@pytest.mark.parametrize(
    ("parameters", "is_default", "binding_language"),
    [
        ({"language": "en"}, True, "en"),
        ({"language": "es", "template": ""}, False, "es"),
    ],
    ids=["legacy_default_row", "legacy_migrated_draft"],
)
def test_a_default_row_with_no_text_reads_the_registered_templates(
    client, parameters, is_default, binding_language
):
    """A language-only default (or a draft migrated from one) is still readable.

    The migration may leave a ``Default*`` row whose body carries no text at
    all. Reads must fall back to the registered component's ``templates``
    instead of raising ``RAGPromptValidationError``.
    """
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        prompt = RAGPrompt(
            class_name="DefaultRAGGenerationPrompt",
            name="legacy language-only",
            parameters=parameters,
            parameters_hash=build_prompt_hash("DefaultRAGGenerationPrompt", parameters),
            is_library=False,
            is_default=is_default,
        )
        db.add(prompt)
        db.flush()
        session = _create_session(db)
        db.add(
            RAGSessionPrompt(
                session_id=session.id,
                slot_path="generation",
                prompt_id=prompt.id,
                language=binding_language,
            )
        )
        db.commit()

        injected = service.inject_prompt_slots(session.id, {})
        resolved = service.resolve_prompt_id_to_component(prompt.id)

    registry = client.app.container["component_registry"]
    expected = registry["DefaultRAGGenerationPrompt"]["class"].metadata["templates"][
        binding_language
    ]
    assert injected["prompt"]["params"]["template"] == expected
    assert resolved["params"]["template"] == expected


def test_delete_with_detach_repoints_bindings_to_a_draft(client):
    """Deleting with detach keeps the session and frees the content hash."""
    session_factory = client.app.container["session_factory"]
    with session_factory() as db:
        service = _service(client, db)
        library = service.create(
            "CustomRAGGenerationPrompt",
            "detachable",
            {"template": _template("{chunks} {input}", "detach")},
        )
        library_id = library.id
        session = _create_session(db)
        service.sync_session_bindings(
            session.id, {}, {"generation": {"prompt_id": library.id}}
        )
        db.commit()

        service.delete(library_id, detach=True)

        binding = db.get(RAGSessionPrompt, (session.id, "generation"))
        draft = db.get(RAGPrompt, binding.prompt_id)
        draft_id = draft.id
        session_id = session.id
        assert draft.id != library_id
        assert draft.class_name == library.class_name
        assert draft.parameters == library.parameters
        assert draft.parameters_hash == build_prompt_hash(
            draft.class_name, draft.parameters
        )
        assert draft.is_library is False
        assert draft.is_default is False

    with session_factory() as db:
        assert db.get(RAGPrompt, library_id) is None
        assert db.get(RAGPrompt, draft_id) is not None
        assert db.get(RAGSessionPrompt, (session_id, "generation")) is not None
