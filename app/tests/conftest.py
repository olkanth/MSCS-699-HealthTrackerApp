# --------------------------------------
# Shared test fixtures.
#
# Tests run against the real Postgres database (dbhealthtracker) to ensure  CHECK/FK constraints are working as expected. 
# Each test gets its own outer transaction that is rolled back afterwards so nothing a test writes.
# --------------------------------------

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.database import engine, get_db
from app.main import app as fastapi_app


@pytest.fixture()
def db_session():
    connection = engine.connect()
    trans = connection.begin()
    TestSession = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    session = TestSession()

    yield session

    session.close()
    trans.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()


def auth_headers(client: TestClient, username: str, role: str, password: str = "testpass123"):
    """Register + log in a throwaway user, return (user_id, {Authorization: ...})."""
    r = client.post(
        "/auth/register",
        json={"username": username, "email": f"{username}@example.com", "password": password, "role": role},
    )
    assert r.status_code == 201, r.text
    user_id = r.json()["id"]

    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]

    return user_id, {"Authorization": f"Bearer {token}"}
