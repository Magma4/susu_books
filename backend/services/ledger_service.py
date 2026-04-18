"""
Susu Books - Ledger Service
Core business logic for recording purchases, sales, and expenses.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Transaction
from schemas import (
    RecordExpenseArgs,
    RecordPurchaseArgs,
    RecordSaleArgs,
    TransactionSource,
    TransactionType,
    normalize_item_name,
    normalize_unit_name,
)
from services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class LedgerService:
    """Creates transactions and keeps inventory synchronized."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory = InventoryService(db)

    async def record_purchase(
        self,
        args: RecordPurchaseArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict[str, object]:
        item = normalize_item_name(args.item)
        unit = normalize_unit_name(args.unit)
        total_amount = round(args.quantity * args.unit_price, 2)

        transaction = Transaction(
            type=TransactionType.purchase,
            item=item,
            quantity=args.quantity,
            unit=unit,
            unit_price=args.unit_price,
            total_amount=total_amount,
            currency=args.currency,
            counterparty=args.supplier,
            category=None,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()

        inventory = await self.inventory.add_stock(
            item=item,
            quantity=args.quantity,
            unit=unit,
            purchase_price=args.unit_price,
        )

        return {
            "transaction_id": transaction.id,
            "item": item,
            "quantity": args.quantity,
            "unit": unit,
            "unit_price": args.unit_price,
            "total_amount": total_amount,
            "currency": args.currency,
            "supplier": args.supplier,
            "new_stock_level": round(inventory.quantity, 2),
        }

    async def record_sale(
        self,
        args: RecordSaleArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict[str, object]:
        item = normalize_item_name(args.item)
        unit = normalize_unit_name(args.unit)
        total_amount = round(args.quantity * args.sale_price, 2)

        transaction = Transaction(
            type=TransactionType.sale,
            item=item,
            quantity=args.quantity,
            unit=unit,
            unit_price=args.sale_price,
            total_amount=total_amount,
            currency=args.currency,
            counterparty=args.customer,
            category=None,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()

        inventory, profit = await self.inventory.remove_stock(
            item=item,
            quantity=args.quantity,
            sale_price=args.sale_price,
            unit=unit,
        )

        low_stock_warning = inventory.quantity <= inventory.low_stock_threshold
        out_of_stock = inventory.quantity <= 0

        return {
            "transaction_id": transaction.id,
            "item": item,
            "quantity": args.quantity,
            "unit": unit,
            "sale_price": args.sale_price,
            "total_amount": total_amount,
            "currency": args.currency,
            "customer": args.customer,
            "profit": profit,
            "remaining_stock": round(inventory.quantity, 2),
            "low_stock_warning": low_stock_warning,
            "out_of_stock": out_of_stock,
        }

    async def record_expense(
        self,
        args: RecordExpenseArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict[str, object]:
        category = args.category.value if hasattr(args.category, "value") else str(args.category)

        transaction = Transaction(
            type=TransactionType.expense,
            item=args.description,
            quantity=None,
            unit=None,
            unit_price=None,
            total_amount=args.amount,
            currency=args.currency,
            counterparty=None,
            category=category,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()

        today_start = datetime.combine(date.today(), datetime.min.time())
        result = await self.db.execute(
            select(func.sum(Transaction.total_amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.created_at >= today_start)
        )
        total_expenses_today = float(result.scalar_one_or_none() or 0.0)

        return {
            "transaction_id": transaction.id,
            "category": category,
            "amount": round(args.amount, 2),
            "currency": args.currency,
            "description": args.description,
            "total_expenses_today": round(total_expenses_today, 2),
        }

    async def get_transactions(
        self,
        *,
        transaction_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        limit: Optional[int] = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        query = select(Transaction).order_by(Transaction.created_at.desc(), Transaction.id.desc())

        if transaction_date:
            start = datetime.combine(transaction_date, datetime.min.time())
            end = datetime.combine(transaction_date, datetime.max.time())
            query = query.where(Transaction.created_at >= start, Transaction.created_at <= end)

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        if offset:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
