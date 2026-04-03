"""
Susu Books - Inventory Service
Manages stock levels using a weighted average cost (WAC) method.
"""

import logging
from datetime import datetime
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import Inventory
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class InventoryService:
    """All inventory mutations go through this service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _get_or_create(self, item: str, unit: Optional[str] = None) -> Inventory:
        """Return existing inventory row for item (case-insensitive), or create a new one."""
        normalized = item.strip().lower()
        result = await self.db.execute(
            select(Inventory).where(Inventory.item == normalized)
        )
        inv = result.scalar_one_or_none()
        if inv is None:
            inv = Inventory(
                item=normalized,
                quantity=0.0,
                unit=unit,
                avg_cost=None,
                last_purchase_price=None,
                low_stock_threshold=settings.default_low_stock_threshold,
                is_low_stock=False,
                updated_at=datetime.utcnow(),
            )
            self.db.add(inv)
            await self.db.flush()
            logger.info("New inventory item created: %s", normalized)
        return inv

    def _update_low_stock_flag(self, inv: Inventory) -> None:
        inv.is_low_stock = inv.quantity <= inv.low_stock_threshold

    # ------------------------------------------------------------------
    # Add stock (from a purchase)
    # ------------------------------------------------------------------

    async def add_stock(
        self,
        item: str,
        quantity: float,
        unit: Optional[str],
        purchase_price: float,
    ) -> Inventory:
        """
        Increase stock by quantity units.
        Recalculate weighted average cost:
            new_avg = (old_qty * old_avg + added_qty * purchase_price) / (old_qty + added_qty)
        """
        inv = await self._get_or_create(item, unit)

        old_qty = inv.quantity
        old_avg = inv.avg_cost or purchase_price  # treat first purchase as baseline

        new_qty = old_qty + quantity
        new_avg = ((old_qty * old_avg) + (quantity * purchase_price)) / new_qty

        inv.quantity = new_qty
        inv.avg_cost = round(new_avg, 4)
        inv.last_purchase_price = purchase_price
        if unit:
            inv.unit = unit
        inv.updated_at = datetime.utcnow()
        self._update_low_stock_flag(inv)

        await self.db.flush()
        return inv

    # ------------------------------------------------------------------
    # Remove stock (from a sale)
    # ------------------------------------------------------------------

    async def remove_stock(
        self,
        item: str,
        quantity: float,
        sale_price: float,
    ) -> Tuple[Inventory, float]:
        """
        Decrease stock by quantity units.
        Computes profit_on_sale = (sale_price - avg_cost) * quantity.
        If stock goes negative, we allow it but log a warning.

        Returns (updated Inventory, profit_on_sale).
        """
        inv = await self._get_or_create(item)

        if inv.quantity < quantity:
            logger.warning(
                "Selling %s x%.2f but only %.2f in stock — allowing negative inventory",
                item, quantity, inv.quantity
            )

        avg_cost = inv.avg_cost or 0.0
        profit_on_sale = (sale_price - avg_cost) * quantity

        inv.quantity = inv.quantity - quantity
        inv.updated_at = datetime.utcnow()
        self._update_low_stock_flag(inv)

        await self.db.flush()
        return inv, profit_on_sale

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def get_item(self, item: str) -> Optional[Inventory]:
        """Return Inventory row for a specific item, or None."""
        normalized = item.strip().lower()
        result = await self.db.execute(
            select(Inventory).where(Inventory.item == normalized)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Inventory]:
        """Return all inventory rows ordered by item name."""
        result = await self.db.execute(
            select(Inventory).order_by(Inventory.item)
        )
        return list(result.scalars().all())

    async def get_low_stock_items(self) -> list[Inventory]:
        """Return items where is_low_stock is True."""
        result = await self.db.execute(
            select(Inventory).where(Inventory.is_low_stock == True)  # noqa: E712
        )
        return list(result.scalars().all())

    async def check_inventory(self, item: Optional[str] = None) -> dict:
        """
        Gemma function: check_inventory handler.
        If item is given, return details for that item.
        If not, return all items + low-stock flags.
        """
        if item:
            inv = await self.get_item(item)
            if inv is None:
                return {
                    "item": item,
                    "found": False,
                    "message": f"No inventory record found for '{item}'.",
                }
            return {
                "found": True,
                "item": inv.item,
                "quantity": inv.quantity,
                "unit": inv.unit,
                "avg_cost": inv.avg_cost,
                "last_purchase_price": inv.last_purchase_price,
                "low_stock_threshold": inv.low_stock_threshold,
                "is_low_stock": inv.is_low_stock,
            }
        else:
            all_items = await self.get_all()
            low_stock = [i for i in all_items if i.is_low_stock]
            return {
                "items": [
                    {
                        "item": i.item,
                        "quantity": i.quantity,
                        "unit": i.unit,
                        "avg_cost": i.avg_cost,
                        "is_low_stock": i.is_low_stock,
                        "low_stock_threshold": i.low_stock_threshold,
                    }
                    for i in all_items
                ],
                "total_items": len(all_items),
                "low_stock_count": len(low_stock),
                "low_stock_items": [i.item for i in low_stock],
            }

    async def update_threshold(self, item: str, threshold: float) -> Optional[Inventory]:
        """Update the low_stock_threshold for a specific item."""
        inv = await self.get_item(item)
        if inv is None:
            return None
        inv.low_stock_threshold = threshold
        self._update_low_stock_flag(inv)
        inv.updated_at = datetime.utcnow()
        await self.db.flush()
        return inv
