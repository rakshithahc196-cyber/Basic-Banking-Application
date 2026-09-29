from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.blacklisted_token import BlacklistedToken


def is_blacklisted(db: Session, token_id: str) -> bool:
    return db.scalar(select(BlacklistedToken.id).where(BlacklistedToken.jti == token_id)) is not None


def blacklist(db: Session, *, token_id: str, expires_at: datetime) -> None:
    db.execute(delete(BlacklistedToken).where(BlacklistedToken.expires_at <= datetime.now(UTC)))
    db.add(BlacklistedToken(jti=token_id, expires_at=expires_at))
    db.flush()