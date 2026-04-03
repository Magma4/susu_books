"""
Susu Books - Ledger Service
Core business logic for recording purchases, sales, and expenses.
All functions are async and receive an SQLAlchemy AsyncSession.
"""

import logging
from datetime import datetime, date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import Transaction, Inventory
from schemas import (
    RecordPurchaseArgs, RecordSaleArgs, RecordExpenseArgs,
    TransactionType, TransactionSource,
)
from services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class LedgerService:
    """Handles creation of all transaction types and triggers inventory updates."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inventory_svc = InventoryService(db)

    # ------------------------------------------------------------------
    # Record Purchase
    # ------------------------------------------------------------------

    async def record_purchase(
        self,
        args: RecordPurchaseArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict:
        """
        Records a stock purchase transaction and updates inventory.

        Returns a dict with:
          - transaction_id
          - item, quantity, unit, unit_price, total_amount, currency
          - new_stock_level
          - new_avg_cost
          - supplier
        """
        total_amount = args.quantity * args.unit_price

        transaction = Transaction(
            type=TransactionType.purchase,
            item=args.item.strip().lower(),
            quantity=args.quantity,
            unit=args.unit,
            unit_price=args.unit_price,
            total_amount=total_amount,
            currency=args.currency,
            counterparty=args.supplier,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()  # get the transaction.id without committing

        # Update inventory
        inv = await self.inventory_svc.add_stock(
            item=args.item.strip().lower(),
            quantity=args.quantity,
            unit=args.unit,
            purchase_price=args.unit_price,
        )

        logger.info(
            "Purchase recorded: %s x%.2f %s @ %s %.2f each (tx#%d)",
            args.item, args.quantity, args.unit, args.currency, args.unit_price, transaction.id
        )

        return {
            "transaction_id": transaction.id,
            "item": args.item,
            "quantity": args.quantity,
            "unit": args.unit,
            "unit_price": args.unit_price,
            "total_amount": total_amount,
            "currency": args.currency,
            "supplier": args.supplier,
            "new_stock_level": inv.quantity,
            "new_avg_cost": inv.avg_cost,
        }

    # ------------------------------------------------------------------
    # Record Sale
    # ------------------------------------------------------------------

    async def record_sale(
        self,
        args: RecordSaleArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict:
        """
        Records a sale transaction and decrements inventory.

        Returns a dict with:
          - transaction_id
          - item, quantity, unit, sale_price, total_revenue, currency
          - profit_on_sale (revenue minus cost basis)
          - remaining_stock
          - low_stock_warning (bool)
          - customer
        """
        total_revenue = args.quantity * args.sale_price

        transaction = Transaction(
            type=TransactionType.sale,
            item=args.item.strip().lower(),
            quantity=args.quantity,
            unit=args.unit,
            unit_price=args.sale_price,
            total_amount=total_revenue,
            currency=args.currency,
            counterparty=args.customer,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()

        # Decrement stock; get result including cost basis for profit calc
        inv, profit_on_sale = await self.inventory_svc.remove_stock(
            item=args.item.strip().lower(),
            quantity=args.quantity,
            sale_price=args.sale_price,
        )

        low_stock_warning = inv.quantity <= inv.low_stock_threshold

        logger.info(
            "Sale recorded: %s x%.2f %s @ %s %.2f each (tx#%d). Profit: %.2f. Remaining: %.2f",
            args.item, args.quantity, args.unit, args.currency,
            args.sale_price, transaction.id, profit_on_sale, inv.quantity
        )

        return {
            "transaction_id": transaction.id,
            "item": args.item,
            "quantity": args.quantity,
            "unit": args.unit,
            "sale_price": args.sale_price,
            "total_revenue": total_revenue,
            "currency": args.currency,
            "customer": args.customer,
            "profit_on_sale": round(profit_on_sale, 2),
            "remaining_stock": inv.quantity,
            "low_stock_warning": low_stock_warning,
        }

    # ------------------------------------------------------------------
    # Record Expense
    # ------------------------------------------------------------------

    async def record_expense(
        self,
        args: RecordExpenseArgs,
        language: str = "en",
        source: TransactionSource = TransactionSource.voice,
        raw_input: Optional[str] = None,
        confidence: float = 1.0,
    ) -> dict:
        """
        Records a non-inventory expense (transport, rent, utilities, staff, etc.).

        Returns a dict with:
          - transaction_id
          - category, description, amount, currency
          - total_expenses_today
        """
        transaction = Transaction(
            type=TransactionType.expense,
            item=args.description,
            quantity=None,
            unit=None,
            unit_price=None,
            total_amount=args.amount,
            currency=args.currency,
            category=args.category,
            notes=args.notes,
            source=source,
            language=language,
            raw_input=raw_input,
            confidence=confidence,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(transaction)
        await self.db.flush()

        # Sum today's expenses
        today = date.today()
        today_start = datetime(today.year, today.month, today.day)
        result = await self.db.execute(
            select(func.sum(Transaction.total_amount))
            .where(Transaction.type == TransactionType.expense)
            .where(Transaction.created_at >= today_start)
        )
        total_expenses_today = result.scalar_one_or_none() or 0.0

        logger.info(
            "Expense recorded: %s - %s %.2f %s (tx#%d)",
            args.category, args.currency, args.amount, args.description, transaction.id
        )

        return {
            "transaction_id": transaction.id,
            "category": args.category,
            "description": args.description,
            "amount": args.amount,
            "currency": args.currency,
            "total_expenses_today": round(total_expenses_today, 2),
        }

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    async def get_transactions(
        self,
        *,
        transaction_date: Optional[date] = None,
        transaction_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Transaction]:
        """Fetch transactions with optional date and type filters."""
        query = select(Transaction).order_by(Transaction.created_at.desc())

        if transaction_date:
            start = datetime(transaction_date.year, transaction_date.month, transaction_date.day)
            end = datetime(transaction_date.year, transaction_date.month, transaction_date.day, 23, 59, 59)
            query = query.where(Transaction.created_at >= start).where(Transaction.created_at <= end)

        if transaction_type:
            query = query.where(Transaction.type == transaction_type)

        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())
