"""The agentic migration renames the LLM-evaluated retrieval family."""

import hashlib
import json

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BASE_REVISION = "f3a4b5c6d7e8"


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


def _insert_prompt(connection, class_name, name, parameters, *, is_default=0):
    return connection.execute(
        sa.text(
            "INSERT INTO rag_prompt "
            "(class_name, name, parameters, parameters_hash, is_library, "
            "is_default, created, last_modified) "
            "VALUES (:class_name, :name, :parameters, :parameters_hash, 0, "
            ":is_default, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ),
        {
            "class_name": class_name,
            "name": name,
            "parameters": json.dumps(parameters),
            "parameters_hash": _prompt_hash(class_name, parameters),
            "is_default": is_default,
        },
    ).lastrowid


def test_upgrade_renames_persisted_agentic_components(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    sufficiency_parameters = {"templates": {"en": "Decide {input}"}, "language": "en"}
    reranker_parameters = {"template": "Pick {input} from {chunks}"}
    generation_parameters = {"template": "Answer {input}"}

    retriever_ref = {
        "component": "LLMEvaluatedDepthRetriever",
        "params": {
            "children": [
                {"component": "BM25Retriever", "params": {"top_k": 5}},
            ],
            "prompt": {
                "component": "DefaultRetrievalSufficiencyPrompt",
                "params": {},
            },
            "llm_model": {"component": "Qwen25_15BInstruct", "params": {}},
        },
    }
    session_parameters = {
        "documents": [],
        "retriever_model": retriever_ref,
    }
    history_parameters = {
        "documents": [],
        "retriever_model": {
            "component": "LLMFilterRetriever",
            "params": {
                "children": [{"component": "BM25Retriever", "params": {"top_k": 8}}],
                "prompt": {
                    "component": "CustomLLMFilterPrompt",
                    "params": {"template": "Pick {input} from {chunks}"},
                },
            },
        },
    }
    pipeline_parameters = {
        "prompt": {
            "component": "CustomRetrievalSufficiencyPrompt",
            "params": {"template": "Decide {input}"},
        },
        "retriever_model": {
            "component": "LLMEvaluatedEnsembleRetriever",
            "params": {
                "children": [
                    {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}
                ],
            },
        },
    }
    history_bindings = {
        "retriever_model.prompt": {
            "class_name": "CustomLLMFilterPrompt",
            "parameters": reranker_parameters,
            "language": "en",
        }
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
                "INSERT INTO rag_pipeline "
                "(id, session_id, name, description, parameters) "
                "VALUES (1, 1, 'pipeline', NULL, :parameters)"
            ),
            {"parameters": json.dumps(pipeline_parameters)},
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_retriever (id, class_name, pipeline_id) "
                "VALUES (1, 'LLMEvaluatedDepthRetriever', 1)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_retriever (id, class_name, pipeline_id) "
                "VALUES (2, 'BM25Retriever', 1)"
            )
        )
        default_prompt_id = _insert_prompt(
            connection,
            "DefaultRetrievalSufficiencyPrompt",
            "Default Retrieval Sufficiency Prompt",
            sufficiency_parameters,
            is_default=1,
        )
        custom_prompt_id = _insert_prompt(
            connection,
            "CustomLLMFilterPrompt",
            "My reranker",
            reranker_parameters,
        )
        generation_prompt_id = _insert_prompt(
            connection,
            "DefaultRAGGenerationPrompt",
            "Default RAG Generation Prompt",
            generation_parameters,
            is_default=1,
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_session_prompt "
                "(session_id, slot_path, prompt_id, language) "
                "VALUES (1, 'retriever_model.prompt', :prompt_id, 'en')"
            ),
            {"prompt_id": default_prompt_id},
        )
        connection.execute(
            sa.text(
                "INSERT INTO parameter_history "
                "(id, session_id, parameters, modified_at, prompt_bindings) "
                "VALUES (1, 1, :parameters, CURRENT_TIMESTAMP, :bindings)"
            ),
            {
                "parameters": json.dumps(history_parameters),
                "bindings": json.dumps(history_bindings),
            },
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        retrievers = dict(
            connection.execute(
                sa.text("SELECT id, class_name FROM rag_retriever ORDER BY id")
            ).fetchall()
        )
        assert retrievers == {1: "AgenticSingleRetriever", 2: "BM25Retriever"}

        prompts = {
            row.id: {
                "class_name": row.class_name,
                "name": row.name,
                "parameters": _load(row.parameters),
                "parameters_hash": row.parameters_hash,
            }
            for row in connection.execute(
                sa.text(
                    "SELECT id, class_name, name, parameters, parameters_hash "
                    "FROM rag_prompt"
                )
            ).fetchall()
        }

        default_prompt = prompts[default_prompt_id]
        assert default_prompt["class_name"] == "DefaultAgenticRetrieverPrompt"
        assert default_prompt["name"] == "Default Agentic Retriever Prompt"
        assert default_prompt["parameters"] == sufficiency_parameters
        assert default_prompt["parameters_hash"] == _prompt_hash(
            "DefaultAgenticRetrieverPrompt", sufficiency_parameters
        )

        custom_prompt = prompts[custom_prompt_id]
        assert custom_prompt["class_name"] == "CustomAgenticRerankerPrompt"
        assert custom_prompt["name"] == "My reranker"
        assert custom_prompt["parameters_hash"] == _prompt_hash(
            "CustomAgenticRerankerPrompt", reranker_parameters
        )

        generation_prompt = prompts[generation_prompt_id]
        assert generation_prompt["class_name"] == "DefaultRAGGenerationPrompt"
        assert generation_prompt["name"] == "Default RAG Generation Prompt"
        assert generation_prompt["parameters_hash"] == _prompt_hash(
            "DefaultRAGGenerationPrompt", generation_parameters
        )

        stored_session = _load(
            connection.execute(
                sa.text("SELECT parameters FROM generative_session WHERE id = 1")
            ).scalar_one()
        )
        assert stored_session["retriever_model"]["component"] == (
            "AgenticSingleRetriever"
        )
        assert stored_session["retriever_model"]["params"]["prompt"] == {
            "component": "DefaultAgenticRetrieverPrompt",
            "params": {},
        }
        assert stored_session["retriever_model"]["params"]["children"] == [
            {"component": "BM25Retriever", "params": {"top_k": 5}}
        ]
        assert stored_session["retriever_model"]["params"]["llm_model"] == {
            "component": "Qwen25_15BInstruct",
            "params": {},
        }

        stored_pipeline = _load(
            connection.execute(
                sa.text("SELECT parameters FROM rag_pipeline WHERE id = 1")
            ).scalar_one()
        )
        assert stored_pipeline["prompt"]["component"] == "CustomAgenticRetrieverPrompt"
        assert stored_pipeline["retriever_model"]["component"] == (
            "AgenticEnsembleRetriever"
        )
        assert stored_pipeline["retriever_model"]["params"]["children"] == [
            {"component": "DenseEmbeddingRetriever", "params": {"top_k": 5}}
        ]

        history_row = connection.execute(
            sa.text(
                "SELECT parameters, prompt_bindings FROM parameter_history WHERE id = 1"
            )
        ).fetchone()
        stored_history = _load(history_row.parameters)
        assert stored_history["retriever_model"]["component"] == (
            "AgenticRerankerRetriever"
        )
        assert stored_history["retriever_model"]["params"]["prompt"]["component"] == (
            "CustomAgenticRerankerPrompt"
        )
        assert stored_history["retriever_model"]["params"]["children"] == [
            {"component": "BM25Retriever", "params": {"top_k": 8}}
        ]

        bindings = _load(history_row.prompt_bindings)
        binding = bindings["retriever_model.prompt"]
        assert binding["class_name"] == "CustomAgenticRerankerPrompt"
        assert binding["parameters"] == reranker_parameters
        assert binding["language"] == "en"

    engine.dispose()


def test_downgrade_restores_the_legacy_component_names(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    sufficiency_parameters = {"templates": {"en": "Decide {input}"}, "language": "en"}
    session_parameters = {
        "documents": [],
        "retriever_model": {
            "component": "LLMEvaluatedDepthRetriever",
            "params": {
                "prompt": {
                    "component": "DefaultRetrievalSufficiencyPrompt",
                    "params": {},
                },
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
                "INSERT INTO rag_pipeline (id, session_id, name, description) "
                "VALUES (1, 1, 'pipeline', NULL)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_retriever (id, class_name, pipeline_id) "
                "VALUES (1, 'LLMEvaluatedDepthRetriever', 1)"
            )
        )
        prompt_id = _insert_prompt(
            connection,
            "DefaultRetrievalSufficiencyPrompt",
            "Default Retrieval Sufficiency Prompt",
            sufficiency_parameters,
            is_default=1,
        )

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, _BASE_REVISION)

    with engine.connect() as connection:
        retriever_name = connection.execute(
            sa.text("SELECT class_name FROM rag_retriever WHERE id = 1")
        ).scalar_one()
        assert retriever_name == "LLMEvaluatedDepthRetriever"

        prompt = connection.execute(
            sa.text(
                "SELECT class_name, name, parameters_hash FROM rag_prompt "
                "WHERE id = :id"
            ),
            {"id": prompt_id},
        ).fetchone()
        assert prompt.class_name == "DefaultRetrievalSufficiencyPrompt"
        assert prompt.name == "Default Retrieval Sufficiency Prompt"
        assert prompt.parameters_hash == _prompt_hash(
            "DefaultRetrievalSufficiencyPrompt", sufficiency_parameters
        )

        stored_session = _load(
            connection.execute(
                sa.text("SELECT parameters FROM generative_session WHERE id = 1")
            ).scalar_one()
        )
        assert stored_session == session_parameters

    engine.dispose()
