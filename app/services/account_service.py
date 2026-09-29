from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.exceptions import BankError, NotFoundError
from app.models.account import Account
from app.models.transaction import Transaction, TransactionType
from app.repositories import account_repository, transaction_repository

MAX_BALANCE = Decimal("9999999999.99")


def get_account(db: Session, user_id: int) -> Account:
    account = account_repository.get_by_user_id(db, user_id)
    if account is None:
        raise NotFoundError("Bank account not found")
    return account


def deposit(db: Session, *, user_id: int, amount: Decimal) -> tuple[Account, Transaction]:
    _validate_amount(amount)
    account = get_account(db, user_id)
    _validate_balance_limit(account.balance + amount)
    try:
        account.balance += amount
        transaction = transaction_repository.create(
            db,
            account_id=account.id,
            transaction_type=TransactionType.DEPOSIT,
            amount=amount,
            reference_id=str(uuid4()),
        )
        db.commit()
        db.refresh(account)
        return account, transaction
    except Exception:
        db.rollback()
        raise


def withdraw(db: Session, *, user_id: int, amount: Decimal) -> tuple[Account, Transaction]:
    _validate_amount(amount)
    account = get_account(db, user_id)
    if account.balance < amount:
        raise BankError("Insufficient balance")
    try:
        account.balance -= amount
        transaction = transaction_repository.create(
            db,
            account_id=account.id,
            transaction_type=TransactionType.WITHDRAW,
            amount=amount,
            reference_id=str(uuid4()),
        )
        db.commit()
        db.refresh(account)
        return account, transaction
    except Exception:
        db.rollback()
        raise


def transfer(
    db: Session,
    *,
    user_id: int,
    recipient_account_number: str,
    amount: Decimal,
) -> tuple[Account, Transaction]:
    _validate_amount(amount)
    sender = get_account(db, user_id)
    recipient = account_repository.get_by_account_number(db, recipient_account_number)
    if recipient is None:
        raise NotFoundError("Recipient account not found")
    if sender.id == recipient.id:
        raise BankError("You cannot transfer money to your own account")

    try:
        locked_accounts = account_repository.get_many_for_update(db, [sender.id, recipient.id])
        accounts_by_id = {account.id: account for account in locked_accounts}
        sender = accounts_by_id[sender.id]
        recipient = accounts_by_id[recipient.id]
        if sender.balance < amount:
            raise BankError("Insufficient balance")
        _validate_balance_limit(recipient.balance + amount)

        reference_id = str(uuid4())
        sender.balance -= amount
        recipient.balance += amount
        sender_transaction = transaction_repository.create(
            db,
            account_id=sender.id,
            transaction_type=TransactionType.TRANSFER_DEBIT,
            amount=amount,
            reference_id=reference_id,
        )
        transaction_repository.create(
            db,
            account_id=recipient.id,
            transaction_type=TransactionType.TRANSFER_CREDIT,
            amount=amount,
            reference_id=reference_id,
        )
        db.commit()
        db.refresh(sender)
        return sender, sender_transaction
    except Exception:
        db.rollback()
        raise


def list_transactions(db: Session, user_id: int) -> list[Transaction]:
    account = get_account(db, user_id)
    return transaction_repository.list_for_account(db, account.id)


def _validate_amount(amount: Decimal) -> None:
    if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
        raise BankError("Amount must be greater than 0 and have at most 2 decimal places")


def _validate_balance_limit(balance: Decimal) -> None:
    if balance > MAX_BALANCE:
        raise BankError("The account balance limit would be exceeded")