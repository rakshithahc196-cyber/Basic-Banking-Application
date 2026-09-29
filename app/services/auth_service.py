import secrets
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationError, ConflictError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories import account_repository, token_repository, user_repository


def register(db: Session, *, name: str, email: str, password: str) -> tuple[User, str]:
    normalized_email = email.strip().lower()
    if user_repository.get_by_email(db, normalized_email):
        raise ConflictError("An account with this email already exists")

    try:
        user = user_repository.create(
            db,
            name=name.strip(),
            email=normalized_email,
            password_hash=hash_password(password),
        )
        account_number = _new_account_number(db)
        account_repository.create(db, user_id=user.id, account_number=account_number)
        db.commit()
        db.refresh(user)
        return user, account_number
    except IntegrityError as error:
        db.rollback()
        raise ConflictError("An account with this email already exists") from error
    except Exception:
        db.rollback()
        raise


def login(db: Session, *, email: str, password: str) -> str:
    user = user_repository.get_by_email(db, email.strip().lower())
    if user is None or not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid email or password")
    token, _token_id, _expires_at = create_access_token(user.id)
    return token


def logout(db: Session, *, token_id: str, expires_at: datetime) -> None:
    token_repository.blacklist(db, token_id=token_id, expires_at=expires_at)
    db.commit()


def _new_account_number(db: Session) -> str:
    for _attempt in range(5):
        candidate = f"{secrets.randbelow(10**10):010d}"
        if not account_repository.account_number_exists(db, candidate):
            return candidate
    raise RuntimeError("Unable to allocate a unique account number")