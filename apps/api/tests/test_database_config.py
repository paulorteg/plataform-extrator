from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.core.config import get_database_url
from app.db.base import Base


def test_database_url_uses_supabase_db_url(monkeypatch):
    monkeypatch.setenv("SUPABASE_DB_URL", "sqlite:///example.db")

    assert get_database_url() == "sqlite:///example.db"


def test_database_url_requires_supabase_db_url(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    with pytest.raises(RuntimeError, match="SUPABASE_DB_URL"):
        get_database_url()


def test_base_metadata_has_no_product_tables():
    assert Base.metadata.tables == {}


def test_alembic_upgrade_head_with_local_database(tmp_path, monkeypatch):
    database_path = tmp_path / "alembic_test.db"
    monkeypatch.setenv("SUPABASE_DB_URL", f"sqlite:///{database_path}")

    config = Config(str(Path("apps/api/alembic.ini")))

    command.upgrade(config, "head")

    assert database_path.exists()
