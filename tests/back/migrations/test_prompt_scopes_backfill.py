"""The prompt-scopes migration moves stored prompts into session bindings."""

import hashlib
import json

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BASE_REVISION = "a7c1e2f3b4d5"


def _config(db_path):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return alembic_cfg


def _prompt_hash(class_name: str, parameters: dict) -> str:
    normalized = json.loads(json.dumps(parameters, sort_keys=True))
    payload = {"class_name": class_name, "parameters": normalized}
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def _load(raw):
    if isinstance(raw, (str, bytes, bytearray)):
        return json.loads(raw)
    return raw


def test_upgrade_moves_prompts_into_bindings_and_history_snapshots(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    generation_template = "Answer {input} using {chunks} legacy"
    sufficiency_template = "Decide {input} from {chunks} legacy"
    history_generation = "Answer {input} using {chunks} older"
    history_sufficiency = "Decide {input} from {chunks} older"

    session_parameters = {
        "documents": [],
        "prompt": {
            "component": "CustomRAGGenerationPrompt",
            "params": {"template": generation_template},
        },
        "retriever_model": {
            "component": "BM25Retriever",
            "params": {
                "vectorizer": {
                    "component": "BagOfWordsConverter",
                    "params": {"k1": 1.5},
                },
                "prompt": {
                    "component": "CustomAgenticRetrieverPrompt",
                    "params": {"template": sufficiency_template},
                },
                "top_k": 5,
            },
        },
    }
    history_parameters = {
        "documents": [],
        "prompt": {
            "component": "CustomRAGGenerationPrompt",
            "params": {"template": history_generation},
        },
        "retriever_model": {
            "component": "BM25Retriever",
            "params": {
                "prompt": {
                    "component": "CustomAgenticRetrieverPrompt",
                    "params": {"template": history_sufficiency},
                },
                "top_k": 5,
            },
        },
    }

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO generative_session "
                "(id, created, last_modified, task_name, model_name, parameters, name) "
                "VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                "'RAGPipeline', :parameters, 'legacy_session')"
            ),
            {"parameters": json.dumps(session_parameters)},
        )
        connection.execute(
            sa.text(
                "INSERT INTO parameter_history "
                "(id, session_id, parameters, modified_at) "
                "VALUES (1, 1, :parameters, CURRENT_TIMESTAMP)"
            ),
            {"parameters": json.dumps(history_parameters)},
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        session_row = connection.execute(
            sa.text("SELECT parameters FROM generative_session WHERE id = 1")
        ).fetchone()
        stored_parameters = _load(session_row.parameters)
        assert "prompt" not in stored_parameters
        assert "prompt_id" not in stored_parameters
        assert "prompt" not in stored_parameters["retriever_model"]["params"]

        bindings = dict(
            connection.execute(
                sa.text(
                    "SELECT slot_path, prompt_id FROM rag_session_prompt "
                    "WHERE session_id = 1"
                )
            ).fetchall()
        )
        assert set(bindings) == {"generation", "retriever_model.prompt"}

        prompts = {
            row.id: {
                "class_name": row.class_name,
                "parameters": _load(row.parameters),
                "parameters_hash": row.parameters_hash,
                "is_default": row.is_default,
                "is_library": row.is_library,
            }
            for row in connection.execute(
                sa.text(
                    "SELECT id, class_name, parameters, parameters_hash, "
                    "is_default, is_library FROM rag_prompt"
                )
            ).fetchall()
        }

        generation_prompt = prompts[bindings["generation"]]
        assert generation_prompt["class_name"] == "CustomRAGGenerationPrompt"
        assert generation_prompt["parameters"] == {"template": generation_template}
        assert generation_prompt["parameters_hash"] == _prompt_hash(
            "CustomRAGGenerationPrompt", {"template": generation_template}
        )
        assert generation_prompt["is_default"] == 0
        assert generation_prompt["is_library"] == 0

        sufficiency_prompt = prompts[bindings["retriever_model.prompt"]]
        assert sufficiency_prompt["class_name"] == "CustomAgenticRetrieverPrompt"
        assert sufficiency_prompt["parameters"] == {"template": sufficiency_template}

        history_row = connection.execute(
            sa.text(
                "SELECT parameters, prompt_bindings FROM parameter_history WHERE id = 1"
            )
        ).fetchone()
        history_parameters_stored = _load(history_row.parameters)
        assert "prompt" not in history_parameters_stored
        assert "prompt" not in history_parameters_stored["retriever_model"]["params"]

        prompt_bindings = _load(history_row.prompt_bindings)
        assert set(prompt_bindings) == {"generation", "retriever_model.prompt"}
        assert prompt_bindings["generation"]["class_name"] == (
            "CustomRAGGenerationPrompt"
        )
        assert prompt_bindings["generation"]["parameters"] == {
            "template": history_generation
        }
        assert prompt_bindings["retriever_model.prompt"]["class_name"] == (
            "CustomAgenticRetrieverPrompt"
        )
        assert prompt_bindings["retriever_model.prompt"]["parameters"] == {
            "template": history_sufficiency
        }

    engine.dispose()


def test_upgrade_keeps_a_legacy_default_text_as_a_draft(tmp_path):
    """A Default* prompt with only a template is not turned into a default."""
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    legacy_template = "Legacy {input} over {chunks}"
    session_parameters = {
        "documents": [],
        "prompt": {
            "component": "DefaultRAGGenerationPrompt",
            "params": {"template": legacy_template},
        },
    }

    engine = sa.create_engine(f"sqlite:///{db_path}")
    legacy_parameters = {"template": legacy_template}
    old_hash = hashlib.sha256(
        json.dumps(legacy_parameters, sort_keys=True).encode()
    ).hexdigest()
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO generative_session "
                "(id, created, last_modified, task_name, model_name, parameters, name) "
                "VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                "'RAGPipeline', :parameters, 'legacy_default_session')"
            ),
            {"parameters": json.dumps(session_parameters)},
        )
        # A legacy database already stores the Default* prompt row the session
        # referenced. It carries only a template and must not stay a default.
        legacy_prompt_id = connection.execute(
            sa.text(
                "INSERT INTO rag_prompt "
                "(class_name, name, parameters, parameters_hash, is_library, "
                "created, last_modified) "
                "VALUES ('DefaultRAGGenerationPrompt', 'legacy', :parameters, "
                ":hash, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "parameters": json.dumps(legacy_parameters),
                "hash": old_hash,
            },
        ).lastrowid

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        binding = connection.execute(
            sa.text(
                "SELECT prompt_id FROM rag_session_prompt "
                "WHERE session_id = 1 AND slot_path = 'generation'"
            )
        ).fetchone()
        assert binding is not None
        assert binding.prompt_id == legacy_prompt_id

        prompt = connection.execute(
            sa.text(
                "SELECT class_name, parameters, is_default FROM rag_prompt "
                "WHERE id = :id"
            ),
            {"id": binding.prompt_id},
        ).fetchone()
        assert prompt.class_name == "DefaultRAGGenerationPrompt"
        assert _load(prompt.parameters) == legacy_parameters
        assert prompt.is_default == 0

        # The migration must never leave a default row that lacks the
        # language templates map: seeding and reads would fail on it.
        defaults = connection.execute(
            sa.text(
                "SELECT parameters FROM rag_prompt "
                "WHERE class_name LIKE 'Default%' AND is_default = 1"
            )
        ).fetchall()
        for row in defaults:
            assert isinstance(_load(row.parameters).get("templates"), dict)

        prompt_sql = connection.execute(
            sa.text(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'table' AND name = 'rag_prompt'"
            )
        ).scalar_one()
        assert "AUTOINCREMENT" in prompt_sql.upper()

    engine.dispose()


@pytest.mark.parametrize(
    "params",
    [
        {"language": "en"},
        {"language": "en", "template": ""},
    ],
    ids=["language_only", "empty_template"],
)
def test_upgrade_leaves_a_default_with_no_text_embedded(tmp_path, params):
    """A Default* ref with no usable text is never turned into an unreadable row."""
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    session_parameters = {
        "documents": [],
        "prompt": {
            "component": "DefaultRAGGenerationPrompt",
            "params": params,
        },
    }

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO generative_session "
                "(id, created, last_modified, task_name, model_name, parameters, name) "
                "VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                "'RAGPipeline', :parameters, 'legacy_empty_default')"
            ),
            {"parameters": json.dumps(session_parameters)},
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        stored = _load(
            connection.execute(
                sa.text("SELECT parameters FROM generative_session WHERE id = 1")
            ).scalar_one()
        )
        # There was no canonical default row to bind, so the legacy reference
        # must stay in parameters; the runtime resolves it from the registered
        # component metadata.
        assert stored["prompt"] == session_parameters["prompt"]

        bindings = connection.execute(
            sa.text("SELECT slot_path FROM rag_session_prompt WHERE session_id = 1")
        ).fetchall()
        assert bindings == []

        # No draft was created for content that has no text at all.
        unreadable = connection.execute(
            sa.text(
                "SELECT id FROM rag_prompt "
                "WHERE class_name = 'DefaultRAGGenerationPrompt' "
                "AND is_default = 0"
            )
        ).fetchall()
        assert unreadable == []

    engine.dispose()


def test_upgrade_keeps_different_templates_maps_of_one_default_class(tmp_path):
    """Two legacy sessions with different default templates keep their own text."""
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    first_template = "First {input} over {chunks}"
    second_template = "Second {input} over {chunks}"
    sessions = {
        1: {"templates": {"en": first_template}, "language": "en"},
        2: {"templates": {"en": second_template}, "language": "en"},
    }

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        for session_id, params in sessions.items():
            connection.execute(
                sa.text(
                    "INSERT INTO generative_session "
                    "(id, created, last_modified, task_name, model_name, "
                    "parameters, name) "
                    "VALUES (:id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                    "'RAGPipeline', :parameters, :name)"
                ),
                {
                    "id": session_id,
                    "parameters": json.dumps(
                        {
                            "documents": [],
                            "prompt": {
                                "component": "DefaultRAGGenerationPrompt",
                                "params": params,
                            },
                        }
                    ),
                    "name": f"legacy_default_{session_id}",
                },
            )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        bound: dict[int, dict] = {}
        for session_id in sessions:
            binding = connection.execute(
                sa.text(
                    "SELECT prompt_id FROM rag_session_prompt "
                    "WHERE session_id = :session_id AND slot_path = 'generation'"
                ),
                {"session_id": session_id},
            ).fetchone()
            assert binding is not None
            row = connection.execute(
                sa.text("SELECT parameters, is_default FROM rag_prompt WHERE id = :id"),
                {"id": binding.prompt_id},
            ).fetchone()
            bound[session_id] = {
                "prompt_id": binding.prompt_id,
                "parameters": _load(row.parameters),
                "is_default": row.is_default,
            }

        # The two sessions must not collapse onto one row: each keeps its text.
        assert bound[1]["prompt_id"] != bound[2]["prompt_id"]
        assert bound[1]["parameters"] == sessions[1]
        assert bound[2]["parameters"] == sessions[2]
        assert bound[1]["parameters"]["templates"]["en"] == first_template
        assert bound[2]["parameters"]["templates"]["en"] == second_template
        # Only the first one can own the class as a built-in; the other is a
        # content-addressed draft with the same Default* class.
        assert bound[1]["is_default"] == 1
        assert bound[2]["is_default"] == 0

    engine.dispose()


def test_downgrade_merges_rows_that_collide_on_the_old_hash(tmp_path):
    """Downgrade keeps one row per parameters hash and repoints pipelines."""
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, "head")

    template = "Shared {input} over {chunks}"
    parameters = {"template": template}
    old_hash = hashlib.sha256(
        json.dumps(parameters, sort_keys=True).encode()
    ).hexdigest()

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO generative_session "
                "(id, created, last_modified, task_name, model_name, parameters, name) "
                "VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                "'RAGPipeline', '{}', 'downgrade_session')"
            )
        )
        first = connection.execute(
            sa.text(
                "INSERT INTO rag_prompt "
                "(class_name, name, parameters, parameters_hash, is_library, "
                "is_default, created, last_modified) "
                "VALUES ('CustomRAGGenerationPrompt', 'first', :parameters, "
                ":hash, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "parameters": json.dumps(parameters),
                "hash": _prompt_hash("CustomRAGGenerationPrompt", parameters),
            },
        ).lastrowid
        second = connection.execute(
            sa.text(
                "INSERT INTO rag_prompt "
                "(class_name, name, parameters, parameters_hash, is_library, "
                "is_default, created, last_modified) "
                "VALUES ('CustomQueryRewritingPrompt', 'second', :parameters, "
                ":hash, 1, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {
                "parameters": json.dumps(parameters),
                "hash": _prompt_hash("CustomQueryRewritingPrompt", parameters),
            },
        ).lastrowid
        connection.execute(
            sa.text(
                "INSERT INTO rag_pipeline "
                "(id, session_id, name, description, parameters, prompt_id) "
                "VALUES (1, 1, 'pipeline', NULL, '{}', :prompt_id)"
            ),
            {"prompt_id": second},
        )

    command.downgrade(alembic_cfg, _BASE_REVISION)

    with engine.connect() as connection:
        rows = connection.execute(
            sa.text("SELECT id FROM rag_prompt WHERE parameters_hash = :hash"),
            {"hash": old_hash},
        ).fetchall()
        assert [row.id for row in rows] == [first]
        pipeline = connection.execute(
            sa.text("SELECT prompt_id FROM rag_pipeline WHERE id = 1")
        ).fetchone()
        assert pipeline.prompt_id == first

        # The previous schema did not use SQLite AUTOINCREMENT on either table;
        # the downgrade must restore it exactly.
        for table in ("generative_session", "rag_prompt"):
            table_sql = connection.execute(
                sa.text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'table' AND name = :name"
                ),
                {"name": table},
            ).scalar_one()
            assert "AUTOINCREMENT" not in table_sql.upper()

    engine.dispose()
