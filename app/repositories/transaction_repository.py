from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction


def create(
    db: Session,
    *,
    account_id: int,
    transaction_type: str,
    amount,
    reference_id: str,
) -> Transaction:
    transaction = Transaction(
        account_id=account_id,
        type=transaction_type,
        amount=amount,
        status="COMPLETED",
        reference_id=reference_id,
    )
    db.add(transaction)
    db.flush()
    return transaction


def list_for_account(db: Session, account_id: int) -> list[Transaction]:
    statement = (
        select(Transaction)
        .where(Transaction.account_id == account_id)
        .order_by(Transaction.created_at.desc(), Transaction.id.desc())
    )
    return list(db.scalars(statement).all())