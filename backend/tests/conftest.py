import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://catalogue:catalogue@localhost:5433/catalogue_test",
)


def _ensure_database() -> None:
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    database_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": database_name},
        ).scalar()
        if not exists:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def engine():
    _ensure_database()
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    def override() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
