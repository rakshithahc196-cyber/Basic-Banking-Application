from fastapi import APIRouter

from app.api.deps import CurrentSession, DatabaseSession
from app.schemas.account import AccountActivityResponse, AccountResponse, TransferRequest
from app.schemas.base import AmountInput
from app.schemas.transaction import TransactionListResponse
from app.services import account_service

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.get(
    "/me",
    response_model=AccountResponse,
    summary="Get the signed-in user's account",
    responses={401: {"description": "Missing, invalid, expired, or revoked bearer token"}, 404: {"description": "Account not found"}},
)
def get_my_account(session: CurrentSession, db: DatabaseSession):
    account = account_service.get_account(db, session.user.id)
    return AccountResponse(
        id=account.id,
        account_number=account.account_number,
        balance=account.balance,
        created_at=account.created_at,
        owner_name=session.user.name,
        owner_email=session.user.email,
    )


@router.post(
    "/deposit",
    response_model=AccountActivityResponse,
    summary="Deposit money",
    responses={400: {"description": "Business rule violation"}, 401: {"description": "Authentication required"}},
)
def deposit(payload: AmountInput, session: CurrentSession, db: DatabaseSession):
    account, transaction = account_service.deposit(db, user_id=session.user.id, amount=payload.amount)
    return AccountActivityResponse(
        message="Deposit completed",
        balance=account.balance,
        transaction=transaction,
    )


@router.post(
    "/withdraw",
    response_model=AccountActivityResponse,
    summary="Withdraw money",
    responses={400: {"description": "Business rule violation"}, 401: {"description": "Authentication required"}},
)
def withdraw(payload: AmountInput, session: CurrentSession, db: DatabaseSession):
    account, transaction = account_service.withdraw(db, user_id=session.user.id, amount=payload.amount)
    return AccountActivityResponse(
        message="Withdrawal completed",
        balance=account.balance,
        transaction=transaction,
    )


@router.post(
    "/transfer",
    response_model=AccountActivityResponse,
    summary="Transfer money to another account",
    responses={400: {"description": "Business rule violation"}, 401: {"description": "Authentication required"}, 404: {"description": "Recipient account not found"}},
)
def transfer(payload: TransferRequest, session: CurrentSession, db: DatabaseSession):
    account, transaction = account_service.transfer(
        db,
        user_id=session.user.id,
        recipient_account_number=payload.recipient_account_number,
        amount=payload.amount,
    )
    return AccountActivityResponse(
        message="Transfer completed",
        balance=account.balance,
        transaction=transaction,
    )


@router.get(
    "/transactions",
    response_model=TransactionListResponse,
    summary="List your transaction history",
    responses={401: {"description": "Authentication required"}, 404: {"description": "Account not found"}},
)
def transactions(session: CurrentSession, db: DatabaseSession):
    return TransactionListResponse(items=account_service.list_transactions(db, session.user.id))