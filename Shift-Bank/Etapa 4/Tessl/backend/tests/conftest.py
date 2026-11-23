import os
import uuid
os.environ.setdefault("ENCRYPTION_KEY", "01234567890123456789012345678901")
os.environ.setdefault("AUDIT_SECRET_KEY", "test_audit_secret_key_32bytes!!")
os.environ.setdefault("ADMIN_SECRET_KEY", "test_admin_secret_key_2026")
os.environ.setdefault("RUN_SCHEDULER", "false")
os.environ.setdefault("TESTING", "true")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.services.account_service import seed_initial_data
from backend.app.services.migration_service import run_stage4_event_sourcing_migration

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15},
    poolclass=StaticPool,
)


@event.listens_for(test_engine, "connect")
def set_test_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class Stage4TestClient(TestClient):
    """TestClient that automatically supplies Idempotency-Key if omitted by legacy tests."""

    def post(self, url, *args, **kwargs):
        url_str = str(url)
        if any(p in url_str for p in ("/api/transfers", "/api/conversions")):
            raw_headers = kwargs.get("headers")
            if raw_headers is None:
                kwargs["headers"] = {"Idempotency-Key": str(uuid.uuid4())}
            elif "omit_idempotency_key" in raw_headers:
                headers = dict(raw_headers)
                headers.pop("omit_idempotency_key", None)
                kwargs["headers"] = headers
        return super().post(url, *args, **kwargs)


@pytest.fixture(scope="function")
def db_session():
    """Create fresh database tables and seed initial mock data for each test."""
    from backend.app.services import audit_service
    from backend.app.database import SessionLocal

    audit_service.set_session_factory(TestingSessionLocal)

    Base.metadata.create_all(bind=test_engine)
    db = TestingSessionLocal()
    seed_initial_data(db)
    run_stage4_event_sourcing_migration(db)
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)
        audit_service.set_session_factory(SessionLocal)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with Stage4TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
