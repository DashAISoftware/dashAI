"""The augmentation prompt cleanup removes rows and references."""

import sqlalchemy as sa
from alembic import command
from alembic.config import Config

_BASE_REVISION = "e2f3a4b5c6d7"


def _config(db_path):
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    return alembic_cfg


def test_upgrade_removes_augmentation_prompts_and_references(tmp_path):
    db_path = tmp_path / "test.db"
    alembic_cfg = _config(db_path)
    command.upgrade(alembic_cfg, _BASE_REVISION)

    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO generative_session "
                "(id, created, last_modified, task_name, model_name, parameters, name) "
                "VALUES (1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'RAGTask', "
                "'RAGPipeline', '{}', 'cleanup_session')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_prompt "
                "(id, class_name, name, parameters, parameters_hash, is_library, "
                "is_default, created, last_modified) VALUES "
                "(10, 'DefaultAugmentationPrompt', 'old default', '{}', "
                "'aug-default', 0, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                "(11, 'CustomRAGGenerationPrompt', 'keep', '{}', 'keep-hash', 1, 0, "
                "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP), "
                "(12, 'CustomAugmentationPrompt', 'old custom', '{}', "
                "'aug-custom', 0, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_session_prompt "
                "(session_id, slot_path, prompt_id) VALUES (1, 'generation', 10)"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO rag_pipeline (id, session_id, name, prompt_id) "
                "VALUES (1, 1, 'pipeline', 10)"
            )
        )

    command.upgrade(alembic_cfg, "head")

    with engine.connect() as connection:
        classes = {
            row[0]
            for row in connection.execute(
                sa.text("SELECT class_name FROM rag_prompt")
            ).fetchall()
        }
        assert classes == {"CustomRAGGenerationPrompt"}

        bindings = connection.execute(
            sa.text("SELECT COUNT(*) FROM rag_session_prompt")
        ).scalar_one()
        assert bindings == 0

        pipeline_prompt = connection.execute(
            sa.text("SELECT prompt_id FROM rag_pipeline WHERE id = 1")
        ).scalar_one()
        assert pipeline_prompt is None

    engine.dispose()
