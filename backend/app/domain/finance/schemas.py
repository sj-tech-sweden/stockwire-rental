from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class FinancialTransactionBase(BaseModel):
    job_id: int | None = None
    transaction_type: str = "payment"
    status: str = "pending"
    amount: Decimal = Decimal("0.00")
    currency: str = "SEK"
    transaction_date: datetime | None = None
    due_date: datetime | None = None


class FinancialTransactionCreate(FinancialTransactionBase):
    pass


class FinancialTransactionUpdate(BaseModel):
    job_id: int | None = None
    transaction_type: str | None = None
    status: str | None = None
    amount: Decimal | None = None
    currency: str | None = None
    transaction_date: datetime | None = None
    due_date: datetime | None = None


class FinancialTransactionRead(FinancialTransactionBase):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
