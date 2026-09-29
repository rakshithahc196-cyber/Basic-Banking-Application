from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.account import Account


def get_by_user_id(db: Session, user_id: int) -> Account | None:
    return db.scalar(select(Account).where(Account.user_id == user_id))


def get_by_account_number(db: Session, account_number: str) -> Account | None:
    return db.scalar(select(Account).where(Account.account_number == account_number))


def get_many_for_update(db: Session, account_ids: list[int]) -> list[Account]:
    statement = (
        select(Account)
        .where(Account.id.in_(account_ids))
        .order_by(Account.id)
        .with_for_update()
    )
    return list(db.scalars(statement).all())


def account_number_exists(db: Session, account_number: str) -> bool:
    return db.scalar(select(Account.id).where(Account.account_number == account_number)) is not None


def create(db: Session, *, user_id: int, account_number: str) -> Account:
    account = Account(user_id=user_id, account_number=account_number)
    db.add(account)
    db.flush()
    return account