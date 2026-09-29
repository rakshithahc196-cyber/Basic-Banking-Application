from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

MoneyAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AmountInput(BaseModel):
    amount: MoneyAmount