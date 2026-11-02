from pathlib import Path
import shutil

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[2]
OLD_HEAD = "f1b4c9d76e20"


def test_original_w02_lineage_cannot_be_silently_marked_current(tmp_path, monkeypatch):
    legacy_scripts = tmp_path / "legacy_alembic"
    shutil.copytree(ROOT / "alembic", legacy_scripts, ignore=shutil.ignore_patterns("__pycache__"))
    old_migration = legacy_scripts / "versions" / "f1b4c9d76e20_add_tool_execution.py"
    source = old_migration.read_text().replace(
        'down_revision: Union[str, None] = "8ab42c17d3e9"',
        'down_revision: Union[str, None] = "e9f4c2b8016a"',
    )
    source = "\n".join(line for line in source.split("\n") if not (
        'op.add_column("itinerary_proposals"' in line
        or 'op.create_index("ix_itinerary_proposals_execution_job_id"' in line
        or 'op.drop_index("ix_itinerary_proposals_execution_job_id"' in line
        or 'op.drop_column("itinerary_proposals"' in line
    ))
    old_migration.write_text(source)
    database_url = f"sqlite:///{tmp_path / 'legacy-original.db'}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(legacy_scripts))
    command.upgrade(config, OLD_HEAD)
    config.set_main_option("script_location", str(ROOT / "alembic"))
    with pytest.raises(RuntimeError, match="incomplete legacy W02 schema"):
        command.upgrade(config, "head")


def test_legacy_w02_and_fresh_databases_receive_speech_metadata(tmp_path, monkeypatch):
    legacy_scripts = tmp_path / "old_alembic"
    shutil.copytree(ROOT / "alembic", legacy_scripts, ignore=shutil.ignore_patterns("__pycache__"))
    old_migration = legacy_scripts / "versions" / "f1b4c9d76e20_add_tool_execution.py"
    old_migration.write_text(old_migration.read_text().replace(
        'down_revision: Union[str, None] = "8ab42c17d3e9"',
        'down_revision: Union[str, None] = "5c81a1e74f2b"',
    ))
    config = Config(str(ROOT / "alembic.ini"))
    for legacy in (True, False):
        database_url = f"sqlite:///{tmp_path / ('legacy.db' if legacy else 'fresh.db')}"
        monkeypatch.setenv("DATABASE_URL", database_url)
        if legacy:
            config.set_main_option("script_location", str(legacy_scripts))
            command.upgrade(config, OLD_HEAD)
        config.set_main_option("script_location", str(ROOT / "alembic"))
        command.upgrade(config, "head")
        engine = create_engine(database_url)
        with engine.begin() as connection:
            columns = {column["name"] for column in inspect(connection).get_columns("chat_logs")}
            assert "speech_metadata" in columns
            connection.execute(text("""
                INSERT INTO chat_logs (session_id, raw_query, normalized_query, answer, sources,
                    hit_level, latency_ms, input_mode, text_emotion, fused_emotion,
                    emotion_confidence, emotion_intensity, emotion_conflict, emotion_modalities,
                    response_strategy, created_at, speech_metadata)
                VALUES ('session', 'q', 'q', 'a', '[]', 'test', 0, 'text', 'neutral',
                    'neutral', 0, 0, 0, '[]', 'default', '2026-01-01', 'kept')
            """))
        command.downgrade(config, OLD_HEAD)
        with engine.connect() as connection:
            assert "speech_metadata" in {column["name"] for column in inspect(connection).get_columns("chat_logs")}
            assert connection.execute(text("SELECT speech_metadata FROM chat_logs")).scalar_one() == "kept"
        engine.dispose()
