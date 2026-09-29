from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.repositories import token_repository, user_repository
from app.db.session import SessionLocal

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    token_id: str
    expires_at: datetime


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_authenticated_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedSession:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        token = credentials.credentials
        claims = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        token_id = claims["jti"]
        user_id = int(claims["sub"])
        expires_at = datetime.fromtimestamp(claims["exp"], UTC)
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError, OverflowError):
        raise unauthorized

    if token_repository.is_blacklisted(db, token_id):
        raise unauthorized
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise unauthorized
    return AuthenticatedSession(user=user, token_id=token_id, expires_at=expires_at)


CurrentSession = Annotated[AuthenticatedSession, Depends(get_authenticated_session)]
DatabaseSession = Annotated[Session, Depends(get_db)]