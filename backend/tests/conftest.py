import pytest
from app.core.database import get_engine, init_db


@pytest.fixture(autouse=True)
def isolated_sqlite_db(tmp_path, monkeypatch):
    db_file = tmp_path / "test_moe_guardian.db"
    test_db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", test_db_url)
    get_engine(test_db_url)
    init_db(test_db_url)
    yield test_db_url