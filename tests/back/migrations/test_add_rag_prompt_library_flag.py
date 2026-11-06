"""The prompt-library flag is added and backfilled for existing custom prompts."""

import sqlalchemy as sa
from alembic import command
from alembic.config import Config


def _config(db_path):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return alembic_cfg


def test_upgrade_backfills_custom_prompts_only(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, "362bcf7193f5")

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO rag_prompt "
                "(class_name, name, parameters, parameters_hash, "
                "created, last_modified) "
                "VALUES (:class_name, :name, :parameters, :hash, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            [
                {
                    "class_name": "CustomRAGGenerationPrompt",
                    "name": "My template",
                    "parameters": '{"template": "Use {chunks} for {input}"}',
                    "hash": "custom-hash",
                },
                {
                    "class_name": "CustomRAGGenerationPrompt",
                    "name": "pipeline_1_CustomRAGGenerationPrompt",
                    "parameters": '{"template": "Internal {chunks} {input}"}',
                    "hash": "internal-hash",
                },
                {
                    "class_name": "DefaultRAGGenerationPrompt",
                    "name": "Default RAG Generation Prompt",
                    "parameters": '{"language": "en"}',
                    "hash": "default-hash",
                },
                {
                    "class_name": "CustomRAGGenerationPrompt",
                    "name": None,
                    "parameters": '{"template": "No name {chunks} {input}"}',
                    "hash": "no-name-hash",
                },
                {
                    "class_name": "CustomRAGGenerationPrompt",
                    "name": "pipelineXnot-internal",
                    "parameters": '{"template": "Underscore {chunks} {input}"}',
                    "hash": "underscore-hash",
                },
            ],
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        rows = dict(
            connection.execute(
                sa.text("SELECT name, is_library FROM rag_prompt")
            ).fetchall()
        )
    assert rows == {
        "My template": 1,
        "pipeline_1_CustomRAGGenerationPrompt": 0,
        "Default RAG Generation Prompt": 0,
        None: 1,
        "pipelineXnot-internal": 1,
    }
    engine.dispose()
