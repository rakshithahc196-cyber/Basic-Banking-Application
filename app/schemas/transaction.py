from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.models.transaction import TransactionType
from app.schemas.base import APIModel


class TransactionResponse(APIModel):
    id: int
    type: TransactionType
    amount: Decimal
    status: str
    reference_id: str
    created_at: datetime


class TransactionListResponse(APIModel):
    items: list[TransactionResponse]
