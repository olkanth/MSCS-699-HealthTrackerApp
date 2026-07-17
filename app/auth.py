# --------------------------------------
# Auth -- password hashing, JWT issuing/verification, and RBAC dependencies
# --------------------------------------

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import services, models
from .config import settings
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    # bcrypt salts automatically and is deliberately slow, to resist brute-forcing a leaked hash.
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    # Re-derives the hash using the salt embedded in password_hash and compares it.
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user: models.User) -> str:
    # Issue a signed JWT for this user, carrying their id/role and an expiry.
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user.id), "role": user.role, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    # Dependency every protected route uses: decodes the bearer token and returns the matching user, or 401.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Verifies the signature and the "exp" expiry claim in one call;
        # PyJWTError covers both a tampered token and an expired one.
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError as exc:
        raise credentials_exception from exc

    # Look the user up fresh rather than trusting the token's claims alone,
    # so a deleted account can't keep using an already-issued token.
    user = services.get_user(db, int(user_id))
    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: str):
    """Dependency factory: require_role("provider", "admin") rejects any other role with 403."""

    def _check(current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not permitted to perform this action.",
            )
        return current_user

    return _check


def ensure_patient_access(db: Session, current_user: models.User, patient_id: int) -> None:
    """Shared ownership check for patients/vital-signs/activity-data routes: provider/admin
    may access any patient's records, a patient may only access their own, it_staff gets
    no clinical-data access (minimum-necessary principle)."""
    if current_user.role in ("provider", "admin"):
        return
    if current_user.role == "patient":
        own_patient = services.get_patient_by_user_id(db, current_user.id)
        if own_patient is not None and own_patient.id == patient_id:
            return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this patient's records.",
    )
