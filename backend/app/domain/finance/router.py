from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.domain.auth.deps import get_current_user
from app.domain.finance.models import FinancialTransaction
from app.domain.finance.schemas import (
    FinancialTransactionCreate,
    FinancialTransactionRead,
    FinancialTransactionUpdate,
)

router = APIRouter(prefix="/finance", tags=["finance"], dependencies=[Depends(get_current_user)])


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {"module": "finance", "status": "scaffolded"}


@router.get("/transactions", response_model=list[FinancialTransactionRead])
def list_transactions(db: Session = Depends(get_db)) -> list[FinancialTransaction]:
    return list(db.scalars(select(FinancialTransaction).order_by(FinancialTransaction.id)).all())


@router.post("/transactions", response_model=FinancialTransactionRead)
def create_transaction(
    payload: FinancialTransactionCreate, db: Session = Depends(get_db)
) -> FinancialTransaction:
    data = payload.model_dump()
    tx = FinancialTransaction(**data)
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.put("/transactions/{transaction_id}", response_model=FinancialTransactionRead)
def update_transaction(
    transaction_id: int, payload: FinancialTransactionUpdate, db: Session = Depends(get_db)
) -> FinancialTransaction:
    tx = db.get(FinancialTransaction, transaction_id)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx
