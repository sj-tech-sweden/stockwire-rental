import os

# Force APP_ENV=test before any app.* imports so Settings() always reads the
# correct value, regardless of what the caller's environment has set.
os.environ["APP_ENV"] = "test"

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.domain.auth.deps import get_current_user, require_admin
from app.domain.auth.models import User
from app.main import app


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session(test_engine) -> Generator[Session, None, None]:
    SessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(test_engine) -> Generator[TestClient, None, None]:
    TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    mock_admin = User(
        id=999,
        email="testadmin@example.com",
        password_hash="irrelevant",
        full_name="Test Admin",
        role="admin",
        notification_channel="both",
        is_active=True,
        is_admin=True,
        auth_source="local",
        created_at=datetime.now(timezone.utc),
    )

    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(delete(table))

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: mock_admin
    app.dependency_overrides[require_admin] = lambda: mock_admin
    with TestClient(app) as test_client:
        setup = test_client.post(
            "/api/v1/auth/setup",
            json={
                "email": "admin@example.com",
                "password": "secret123",
                "full_name": "Admin User",
                "role": "admin",
                "is_active": True,
            },
        )
        assert setup.status_code == 201
        token = setup.json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client
    app.dependency_overrides.clear()
