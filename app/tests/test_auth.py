# --------------------------------------
# Auth tests: register/login, wrong password, bad/expired token, RBAC.
# --------------------------------------

from datetime import datetime, timedelta, timezone

import jwt

from app.auth import hash_password, verify_password
from app.config import settings
from app.tests.conftest import auth_headers


# hash_password/verify_password round-trip: a hash never equals the plain
# password, the right password verifies, and a wrong one doesn't.
def test_hash_password_and_verify_roundtrip():
    hashed = hash_password("mypassword123")
    assert hashed != "mypassword123"
    assert verify_password("mypassword123", hashed)
    assert not verify_password("wrongpassword", hashed)


# End-to-end happy path: register a login account, then log in with the
# same credentials and get back a bearer token. Also checks the register
# response never leaks the password or its hash.
def test_register_and_login_success(client):
    r = client.post(
        "/auth/register",
        json={"username": "authuser1", "email": "authuser1@example.com", "password": "supersecret1", "role": "patient"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "authuser1"
    assert "password" not in body and "password_hash" not in body

    r = client.post("/auth/login", data={"username": "authuser1", "password": "supersecret1"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert "access_token" in r.json()


# Logging in with the right username but the wrong password is rejected.
def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        json={"username": "authuser2", "email": "authuser2@example.com", "password": "supersecret1", "role": "patient"},
    )
    r = client.post("/auth/login", data={"username": "authuser2", "password": "wrongpass"})
    assert r.status_code == 401


# Logging in as a username that was never registered is rejected the same
# way as a wrong password (401), so a client can't tell which one was wrong.
def test_login_unknown_user(client):
    r = client.post("/auth/login", data={"username": "doesnotexist", "password": "whatever1"})
    assert r.status_code == 401


# The users table has a UNIQUE constraint on username; registering the same
# username twice surfaces as a 409, not a raw database error.
def test_duplicate_username_registration_conflict(client):
    payload = {"username": "dupeuser", "email": "dupe1@example.com", "password": "supersecret1", "role": "patient"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json={**payload, "email": "dupe2@example.com"})
    assert r2.status_code == 409


# role is a Literal["patient","provider","admin","it_staff"] on the schema,
# so an unrecognized role is rejected as a 422 before it reaches the DB.
def test_invalid_role_rejected(client):
    r = client.post(
        "/auth/register",
        json={"username": "badrole", "email": "badrole@example.com", "password": "supersecret1", "role": "superadmin"},
    )
    assert r.status_code == 422


# No Authorization header at all -> 401, on a route that requires a token.
def test_protected_endpoint_requires_token(client):
    r = client.get("/patients/1")
    assert r.status_code == 401


# A syntactically-wrong bearer token (not a real JWT) is rejected as 401,
# same as a missing one.
def test_garbage_token_rejected(client):
    r = client.get("/patients/1", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


# A token that's otherwise well-formed and correctly signed, but past its
# "exp" claim, is rejected -- jwt.decode() enforces expiry automatically.
def test_expired_token_rejected(client):
    user_id, _ = auth_headers(client, "expuser1", "patient")
    expired_payload = {
        "sub": str(user_id),
        "role": "patient",
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    token = jwt.encode(expired_payload, settings.secret_key, algorithm=settings.algorithm)
    r = client.get("/patients/1", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


# A valid, unexpired token for the wrong role gets 403 (authenticated but
# not authorized), which is distinct from the 401s above (not authenticated
# at all) -- lets a client tell "log in again" apart from "you can't do this".
def test_role_restricted_endpoint_returns_403_not_401_for_valid_token(client):
    _, patient_headers = auth_headers(client, "rbacuser1", "patient")
    r = client.get("/patients/", headers=patient_headers)  # list-all is provider/admin only
    assert r.status_code == 403
