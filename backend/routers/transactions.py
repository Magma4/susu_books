"""
Susu Books - Transactions Router
CRUD endpoints for querying and managing transactions.
"""

from datetime import date as date_type, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Transaction
from schemas import TransactionOut, TransactionCreate, TransactionUpdate, TransactionType
from services.ledger_service import LedgerService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
async def list_transactions(
    date: Optional[str] = Query(
        None,
        description="Filter by date in YYYY-MM-DD format",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    type: Optional[TransactionType] = Query(None, description="Filter by type: purchase, sale, expense"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    List transactions with optional date and type filters.
    Results are ordered newest-first.
    """
    svc = LedgerService(db)

    parsed_date: Optional[date_type] = None
    if date:
        try:
            parsed_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format: {date}. Use YYYY-MM-DD.",
            )

    transactions = await svc.get_transactions(
        transaction_date=parsed_date,
        transaction_type=type.value if type else None,
        limit=limit,
        offset=offset,
    )
    return [TransactionOut.model_validate(t) for t in transactions]


@router.get("/{transaction_id}", response_model=TransactionOut)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single transaction by ID."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )
    return TransactionOut.model_validate(tx)


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
async def create_transaction_manual(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Manually create a transaction (bypasses Gemma — for direct API use).
    Note: This does NOT update inventory. Use the /api/chat endpoint for
    voice-based transactions that should update stock.
    """
    tx = Transaction(
        type=payload.type,
        item=payload.item.strip().lower(),
        quantity=payload.quantity,
        unit=payload.unit,
        unit_price=payload.unit_price,
        total_amount=payload.total_amount,
        currency=payload.currency,
        counterparty=payload.counterparty,
        category=payload.category,
        notes=payload.notes,
        source=payload.source,
        language=payload.language,
        raw_input=payload.raw_input,
        confidence=payload.confidence,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.patch("/{transaction_id}", response_model=TransactionOut)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a transaction (correcting AI-extracted data)."""
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tx, field, value)
    tx.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a transaction record.
    WARNING: Does not reverse inventory changes — use with care.
    """
    result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = result.scalar_one_or_none()
    if tx is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {transaction_id} not found.",
        )
    await db.delete(tx)
