import os
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session
from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None
_current_db_url: Optional[str] = None


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", settings.database_url)


def get_engine(db_url: Optional[str] = None) -> Engine:
    global _engine, _SessionLocal, _current_db_url
    target_url = db_url or get_database_url()
    if _engine is None or _current_db_url != target_url:
        connect_args = {"check_same_thread": False} if target_url.startswith("sqlite") else {}
        _engine = create_engine(target_url, connect_args=connect_args, future=True)
        if target_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
        _current_db_url = target_url
    return _engine


def get_session_factory(db_url: Optional[str] = None) -> sessionmaker:
    get_engine(db_url)
    assert _SessionLocal is not None
    return _SessionLocal


def init_db(db_url: Optional[str] = None) -> None:
    from app.models import orm_models  # noqa: F401
    engine = get_engine(db_url)
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    init_db()
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()