from datetime import datetime
from decimal import Decimal

from pydantic import EmailStr, Field

from app.schemas.base import APIModel, MoneyAmount
from app.schemas.transaction import TransactionResponse


class AccountResponse(APIModel):
    id: int
    account_number: str
    balance: Decimal
    created_at: datetime
    owner_name: str
    owner_email: EmailStr


class TransferRequest(APIModel):
    recipient_account_number: str = Field(min_length=10, max_length=10, pattern=r"^\d{10}$")
    amount: MoneyAmount


class AccountActivityResponse(APIModel):
    message: str
    balance: Decimal
    transaction: TransactionResponse