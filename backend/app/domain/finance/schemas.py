from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


ALLOWED_TRANSACTION_TYPES = {
    "rental",
    "deposit",
    "payment",
    "refund",
    "fee",
    "discount",
}

ALLOWED_TRANSACTION_STATUSES = {
    "pending",
    "completed",
    "failed",
    "cancelled",
    "refunded",
}


class FinancialTransactionBase(BaseModel):
    job_id: int | None = None
    transaction_type: str = "payment"
    status: str = "pending"
    amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    currency: str = Field(default="SEK", min_length=3, max_length=3)
    transaction_date: datetime | None = None
    due_date: datetime | None = None

    @field_validator("transaction_type")
    @classmethod
    def _validate_transaction_type(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of: {', '.join(sorted(ALLOWED_TRANSACTION_TYPES))}")
        return normalized

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str) -> str:
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_TRANSACTION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_TRANSACTION_STATUSES))}")
        return normalized

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str) -> str:
        normalized = str(value or "").strip().upper()
        if len(normalized) != 3:
            raise ValueError("currency must be a 3-letter code")
        return normalized


class FinancialTransactionCreate(FinancialTransactionBase):
    pass


class FinancialTransactionUpdate(BaseModel):
    job_id: int | None = None
    transaction_type: str | None = None
    status: str | None = None
    amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    currency: str | None = None
    transaction_date: datetime | None = None
    due_date: datetime | None = None

    @field_validator("transaction_type")
    @classmethod
    def _validate_transaction_type(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_TRANSACTION_TYPES:
            raise ValueError(f"transaction_type must be one of: {', '.join(sorted(ALLOWED_TRANSACTION_TYPES))}")
        return normalized

    @field_validator("status")
    @classmethod
    def _validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().lower()
        if normalized not in ALLOWED_TRANSACTION_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(ALLOWED_TRANSACTION_STATUSES))}")
        return normalized

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value or "").strip().upper()
        if len(normalized) != 3:
            raise ValueError("currency must be a 3-letter code")
        return normalized


class FinancialTransactionRead(FinancialTransactionBase):
    id: int
    created_at: datetime
    job_code: str | None = None
    customer_name: str | None = None
    days_overdue: int = 0
    is_overdue: bool = False

    model_config = {"from_attributes": True}


class FinancialTransactionListQuery(BaseModel):
    status: str | None = None
    transaction_type: str | None = None
    job_id: int | None = None
    customer_name: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    overdue_only: bool = False


class FinanceSummaryRead(BaseModel):
    currency: str = "SEK"
    total_transactions: int = 0
    pending_count: int = 0
    overdue_count: int = 0
    completed_count: int = 0
    pending_amount: Decimal = Decimal("0.00")
    overdue_amount: Decimal = Decimal("0.00")
    completed_amount: Decimal = Decimal("0.00")


class JobFinanceInsightRead(BaseModel):
    job_id: int
    job_code: str
    customer_name: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    rental_days: int = 1
    requirement_lines: int = 0
    quantity_required_total: int = 0
    quantity_picked_total: int = 0
    completion_percent: int = 0
    estimated_value: Decimal = Decimal("0.00")
    transaction_total: Decimal = Decimal("0.00")
    completed_transaction_total: Decimal = Decimal("0.00")


class FinanceJobInsightsRead(BaseModel):
    jobs_total: int = 0
    jobs_active: int = 0
    jobs_completed: int = 0
    jobs_cancelled: int = 0
    projected_total_value: Decimal = Decimal("0.00")
    projected_active_value: Decimal = Decimal("0.00")
    projected_completed_value: Decimal = Decimal("0.00")
    sales_total_value: Decimal = Decimal("0.00")
    sales_paid_value: Decimal = Decimal("0.00")
    sales_unpaid_value: Decimal = Decimal("0.00")
    invoice_paid_jobs: int = 0
    invoice_unpaid_jobs: int = 0
    transaction_total: Decimal = Decimal("0.00")
    collected_total: Decimal = Decimal("0.00")
    top_jobs: list[JobFinanceInsightRead] = Field(default_factory=list)
