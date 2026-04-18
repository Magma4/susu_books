"""
Susu Books - Inventory Router
Endpoints for querying and configuring inventory.
"""

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import InventoryOut, InventoryUpdate
from services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory", tags=["inventory"])


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@router.get("", response_model=list[InventoryOut])
async def list_inventory(
    low_stock_only: bool = Query(False, description="Return only items below their threshold"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all inventory items with current stock levels.
    Optionally filter to only low-stock items.
    """
    svc = InventoryService(db)
    if low_stock_only:
        items = await svc.get_low_stock_items()
    else:
        items = await svc.get_all()
    return [InventoryOut.model_validate(i) for i in items]


@router.get("/{item_name}", response_model=InventoryOut)
async def get_inventory_item(
    item_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Get inventory details for a specific item (case-insensitive)."""
    svc = InventoryService(db)
    inv = await svc.get_item(item_name)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory record found for '{item_name}'.",
        )
    return InventoryOut.model_validate(inv)


@router.patch("/{item_name}", response_model=InventoryOut)
async def update_inventory_settings(
    item_name: str,
    payload: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Update inventory settings for a specific item.
    Currently supports: low_stock_threshold, unit.
    """
    svc = InventoryService(db)
    inv = await svc.get_item(item_name)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory record found for '{item_name}'.",
        )

    if payload.low_stock_threshold is not None:
        inv = await svc.update_threshold(item_name, payload.low_stock_threshold)

    if payload.unit is not None:
        inv.unit = payload.unit
        inv.updated_at = utcnow()
        await db.flush()
        await db.refresh(inv)

    return InventoryOut.model_validate(inv)


@router.get("/check/alerts", response_model=dict)
async def inventory_alerts(
    db: AsyncSession = Depends(get_db),
):
    """
    Return a summary of inventory alerts: low-stock items, zero-stock items.
    Used by the frontend "What needs action" pane.
    """
    svc = InventoryService(db)
    all_items = await svc.get_all()
    low_stock = [i for i in all_items if i.is_low_stock and i.quantity > 0]
    zero_stock = [i for i in all_items if i.quantity <= 0]

    return {
        "total_items": len(all_items),
        "low_stock_count": len(low_stock),
        "zero_stock_count": len(zero_stock),
        "low_stock_items": [
            {
                "item": i.item,
                "quantity": i.quantity,
                "unit": i.unit,
                "threshold": i.low_stock_threshold,
            }
            for i in low_stock
        ],
        "zero_stock_items": [
            {"item": i.item, "unit": i.unit}
            for i in zero_stock
        ],
    }
