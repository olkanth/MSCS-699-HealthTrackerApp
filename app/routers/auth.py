# --------------------------------------
# Auth routes -- register a login account, then exchange credentials for
# a bearer token used on every other protected endpoint.
# --------------------------------------

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import services, schemas
from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=schemas.UserOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": schemas.ErrorResponse, "description": "Username or email already registered"}},
)
async def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a login account. Role determines what the account can later access."""
    try:
        user = services.create_user(
            db,
            username=user_in.username,
            email=user_in.email,
            password_hash=hash_password(user_in.password),
            role=user_in.role,
        )
    except services.DuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return user


@router.post(
    "/login",
    response_model=schemas.Token,
    responses={401: {"model": schemas.ErrorResponse, "description": "Incorrect username or password"}},
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Exchange a username/password for a bearer token (OAuth2 password flow)."""
    user = services.get_user_by_username(db, form_data.username)
    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user)
    return schemas.Token(access_token=token)
