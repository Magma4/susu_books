"""
Susu Books - Inventory Service
Tracks stock using weighted average cost and rebuilds inventory when needed.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from models import Inventory, Transaction
from schemas import TransactionType, normalize_item_name, normalize_unit_name

logger = logging.getLogger(__name__)
settings = get_settings()


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class InventoryService:
    """All inventory mutations and queries flow through this service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create(self, item: str, unit: Optional[str] = None) -> Inventory:
        normalized_item = normalize_item_name(item)
        result = await self.db.execute(
            select(Inventory).where(Inventory.item == normalized_item)
        )
        inventory = result.scalar_one_or_none()
        if inventory is None:
            inventory = Inventory(
                item=normalized_item,
                quantity=0.0,
                unit=normalize_unit_name(unit) if unit else None,
                avg_cost=None,
                last_purchase_price=None,
                last_sale_price=None,
                low_stock_threshold=settings.default_low_stock_threshold,
                is_low_stock=True,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            self.db.add(inventory)
            await self.db.flush()
        return inventory

    @staticmethod
    def _update_status(inventory: Inventory) -> None:
        inventory.is_low_stock = inventory.quantity <= inventory.low_stock_threshold

    def _build_item_payload(self, inventory: Inventory) -> dict[str, object]:
        status = "ok"
        if inventory.quantity <= 0:
            status = "out"
        elif inventory.quantity <= inventory.low_stock_threshold:
            status = "low"

        return {
            "item": inventory.item,
            "quantity": round(inventory.quantity, 2),
            "unit": inventory.unit,
            "avg_cost": round(inventory.avg_cost, 4) if inventory.avg_cost is not None else None,
            "last_purchase_price": inventory.last_purchase_price,
            "last_sale_price": inventory.last_sale_price,
            "low_stock_threshold": inventory.low_stock_threshold,
            "status": status,
        }

    async def add_stock(
        self,
        item: str,
        quantity: float,
        unit: Optional[str],
        purchase_price: float,
    ) -> Inventory:
        inventory = await self._get_or_create(item, unit)

        old_quantity = inventory.quantity
        old_average = inventory.avg_cost if inventory.avg_cost is not None else purchase_price
        new_quantity = old_quantity + quantity
        new_average = ((old_quantity * old_average) + (quantity * purchase_price)) / new_quantity

        inventory.quantity = round(new_quantity, 4)
        inventory.avg_cost = round(new_average, 4)
        inventory.last_purchase_price = purchase_price
        if unit:
            inventory.unit = normalize_unit_name(unit)
        inventory.updated_at = utcnow()
        self._update_status(inventory)

        await self.db.flush()
        return inventory

    async def remove_stock(
        self,
        item: str,
        quantity: float,
        sale_price: float,
        unit: Optional[str] = None,
    ) -> tuple[Inventory, float]:
        inventory = await self._get_or_create(item, unit)

        if inventory.quantity < quantity:
            logger.warning(
                "Selling %s x%.2f with only %.2f in stock; allowing negative inventory.",
                inventory.item,
                quantity,
                inventory.quantity,
            )

        average_cost = inventory.avg_cost or 0.0
        total_profit = (sale_price - average_cost) * quantity

        inventory.quantity = round(inventory.quantity - quantity, 4)
        inventory.last_sale_price = sale_price
        if unit and not inventory.unit:
            inventory.unit = normalize_unit_name(unit)
        inventory.updated_at = utcnow()
        self._update_status(inventory)

        await self.db.flush()
        return inventory, round(total_profit, 2)

    async def get_item(self, item: str) -> Optional[Inventory]:
        normalized_item = normalize_item_name(item)
        result = await self.db.execute(
            select(Inventory).where(Inventory.item == normalized_item)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Inventory]:
        result = await self.db.execute(
            select(Inventory).order_by(Inventory.quantity.asc(), Inventory.item.asc())
        )
        return list(result.scalars().all())

    async def get_low_stock_items(self) -> list[Inventory]:
        result = await self.db.execute(
            select(Inventory)
            .where(Inventory.is_low_stock == True)  # noqa: E712
            .order_by(Inventory.quantity.asc(), Inventory.item.asc())
        )
        return list(result.scalars().all())

    async def check_inventory(self, item: Optional[str] = None) -> dict[str, object]:
        if item:
            inventory = await self.get_item(item)
            if inventory is None:
                return {
                    "items": [],
                    "item": normalize_item_name(item),
                    "found": False,
                }

            payload = self._build_item_payload(inventory)
            return {
                "items": [payload],
                "item": payload["item"],
                "quantity": payload["quantity"],
                "unit": payload["unit"],
                "avg_cost": payload["avg_cost"],
                "last_purchase_price": payload["last_purchase_price"],
                "last_sale_price": payload["last_sale_price"],
                "status": payload["status"],
                "found": True,
            }

        items = await self.get_all()
        return {
            "items": [self._build_item_payload(item_row) for item_row in items],
        }

    async def update_threshold(self, item: str, threshold: float) -> Optional[Inventory]:
        inventory = await self.get_item(item)
        if inventory is None:
            return None

        inventory.low_stock_threshold = threshold
        inventory.updated_at = utcnow()
        self._update_status(inventory)
        await self.db.flush()
        return inventory

    async def rebuild_from_transactions(self) -> None:
        existing_thresholds = {
            inventory.item: inventory.low_stock_threshold
            for inventory in await self.get_all()
        }

        await self.db.execute(delete(Inventory))
        await self.db.flush()

        result = await self.db.execute(
            select(Transaction).order_by(Transaction.created_at.asc(), Transaction.id.asc())
        )
        transactions = list(result.scalars().all())

        for transaction in transactions:
            if transaction.type == TransactionType.purchase:
                inventory = await self._get_or_create(transaction.item, transaction.unit)
                inventory.low_stock_threshold = existing_thresholds.get(
                    inventory.item,
                    settings.default_low_stock_threshold,
                )
                quantity = transaction.quantity or 0.0
                unit_price = transaction.unit_price or 0.0
                old_quantity = inventory.quantity
                old_average = inventory.avg_cost if inventory.avg_cost is not None else unit_price
                new_quantity = old_quantity + quantity
                if new_quantity > 0:
                    inventory.avg_cost = round(
                        ((old_quantity * old_average) + (quantity * unit_price)) / new_quantity,
                        4,
                    )
                inventory.quantity = round(new_quantity, 4)
                inventory.last_purchase_price = unit_price or inventory.last_purchase_price
                inventory.unit = normalize_unit_name(transaction.unit) if transaction.unit else inventory.unit
                inventory.updated_at = utcnow()
                self._update_status(inventory)
                continue

            if transaction.type == TransactionType.sale:
                inventory = await self._get_or_create(transaction.item, transaction.unit)
                inventory.low_stock_threshold = existing_thresholds.get(
                    inventory.item,
                    settings.default_low_stock_threshold,
                )
                inventory.quantity = round(inventory.quantity - (transaction.quantity or 0.0), 4)
                inventory.last_sale_price = transaction.unit_price or inventory.last_sale_price
                inventory.unit = normalize_unit_name(transaction.unit) if transaction.unit else inventory.unit
                inventory.updated_at = utcnow()
                self._update_status(inventory)

        await self.db.flush()
