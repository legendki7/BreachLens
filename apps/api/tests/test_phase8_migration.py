import importlib.util
from pathlib import Path

from sqlalchemy.dialects import postgresql

from app.duels.repository import SqlAlchemyDuelRepository


def test_phase8_migration_links_to_phase2_and_has_upgrade_and_downgrade() -> None:
    path = (
        Path(__file__).parents[1]
        / "migrations"
        / "versions"
        / "20260825_0003_phase_8_duel_evidence.py"
    )
    spec = importlib.util.spec_from_file_location("phase8_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "20260825_0003"
    assert module.down_revision == "20260816_0002"
    assert callable(module.upgrade)
    assert callable(module.downgrade)


def test_execution_context_query_compiles_for_postgresql() -> None:
    statement = SqlAlchemyDuelRepository._context_statement(__import__("uuid").uuid4())
    rendered = str(statement.compile(dialect=postgresql.dialect()))
    assert "duels" in rendered
    assert "target_models" in rendered
    assert "policy_profiles" in rendered
