"""
Susu Books - Transactions Router
CRUD endpoints for querying and managing transactions.
"""

from datetime import UTC, date as date_type, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Transaction
from schemas import (
    RecordExpenseArgs,
    RecordPurchaseArgs,
    RecordSaleArgs,
    TransactionOut,
    TransactionCreate,
    TransactionUpdate,
    TransactionType,
    normalize_currency_code,
    normalize_item_name,
    normalize_unit_name,
)
from services.inventory_service import InventoryService
from services.ledger_service import LedgerService

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


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
    Manually create a transaction while keeping inventory in sync.
    """
    ledger = LedgerService(db)

    if payload.type == TransactionType.purchase:
        unit_price = payload.unit_price
        if unit_price is None and payload.quantity:
            unit_price = payload.total_amount / payload.quantity
        if payload.quantity is None or payload.unit is None or unit_price is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Manual purchase creation requires quantity, unit, and unit_price or total_amount.",
            )
        result = await ledger.record_purchase(
            RecordPurchaseArgs(
                item=payload.item,
                quantity=payload.quantity,
                unit=payload.unit,
                unit_price=unit_price,
                supplier=payload.counterparty,
                currency=payload.currency,
                notes=payload.notes,
            ),
            language=payload.language,
            source=payload.source,
            raw_input=payload.raw_input,
            confidence=payload.confidence,
        )
        transaction_id = int(result["transaction_id"])
    elif payload.type == TransactionType.sale:
        sale_price = payload.unit_price
        if sale_price is None and payload.quantity:
            sale_price = payload.total_amount / payload.quantity
        if payload.quantity is None or payload.unit is None or sale_price is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Manual sale creation requires quantity, unit, and unit_price or total_amount.",
            )
        result = await ledger.record_sale(
            RecordSaleArgs(
                item=payload.item,
                quantity=payload.quantity,
                unit=payload.unit,
                sale_price=sale_price,
                customer=payload.counterparty,
                currency=payload.currency,
                notes=payload.notes,
            ),
            language=payload.language,
            source=payload.source,
            raw_input=payload.raw_input,
            confidence=payload.confidence,
        )
        transaction_id = int(result["transaction_id"])
    else:
        result = await ledger.record_expense(
            RecordExpenseArgs(
                category=payload.category or "other",
                amount=payload.total_amount,
                description=payload.item,
                currency=payload.currency,
                notes=payload.notes,
            ),
            language=payload.language,
            source=payload.source,
            raw_input=payload.raw_input,
            confidence=payload.confidence,
        )
        transaction_id = int(result["transaction_id"])

    tx_result = await db.execute(
        select(Transaction).where(Transaction.id == transaction_id)
    )
    tx = tx_result.scalar_one()
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
        if field == "item" and isinstance(value, str):
            value = normalize_item_name(value)
        elif field == "unit" and isinstance(value, str):
            value = normalize_unit_name(value)
        elif field == "currency":
            value = normalize_currency_code(value)
        setattr(tx, field, value)

    if tx.type in {TransactionType.purchase, TransactionType.sale}:
        if "quantity" in update_data or "unit_price" in update_data:
            if tx.quantity and tx.unit_price:
                tx.total_amount = tx.quantity * tx.unit_price
    elif tx.type == TransactionType.expense and "total_amount" in update_data and not tx.item:
        tx.item = tx.category or "expense"

    tx.updated_at = utcnow()

    inventory_service = InventoryService(db)
    await inventory_service.rebuild_from_transactions()
    await db.flush()
    await db.refresh(tx)
    return TransactionOut.model_validate(tx)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a transaction record and rebuild inventory from the remaining ledger.
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
    await db.flush()
    inventory_service = InventoryService(db)
    await inventory_service.rebuild_from_transactions()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
