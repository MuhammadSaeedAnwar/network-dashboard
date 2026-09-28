import os

os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PASSWORD", "test-only-not-used")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    # The app's lifespan normally calls init_db(), which uses the real
    # module-level engine (pointing at Postgres). Tests use an isolated
    # in-memory SQLite session instead (already created via db_session),
    # so the real startup schema creation is skipped here.
    with patch("app.main.init_db"):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()


AUTHORIZED_HOST_PAYLOAD = {
    "name": "Test Router",
    "address": "192.168.1.1",
    "description": "My own home router",
    "authorized_confirmation": True,
}
