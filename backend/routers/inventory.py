"""
Susu Books - Inventory Router
Endpoints for querying and configuring inventory.
"""

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import InventoryOut, InventorySetup, InventoryUpdate, normalize_currency_code, normalize_unit_name
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


@router.post("/setup", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
async def setup_inventory_item(
    payload: InventorySetup,
    db: AsyncSession = Depends(get_db),
):
    """
    Create or replace an inventory item and its sales pricing rule.

    Example: 40 plantains, priced as 8 GHS per 4 pieces. Voice sales can then
    infer that "plantain 8 cedis" means 4 pieces sold.
    """
    svc = InventoryService(db)
    inv = await svc.setup_item(payload)
    await db.refresh(inv)
    return InventoryOut.model_validate(inv)


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
    Update inventory settings or adjust stock levels directly.
    Supports adjusting: quantity, avg_cost, low_stock_threshold, unit, and selling rules.
    """
    svc = InventoryService(db)
    inv = await svc.get_item(item_name)
    if inv is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory record found for '{item_name}'.",
        )

    if payload.quantity is not None:
        inv.quantity = round(payload.quantity, 4)
        inv.is_low_stock = inv.quantity <= inv.low_stock_threshold
        inv.updated_at = utcnow()
        await db.flush()
        await db.refresh(inv)

    if payload.avg_cost is not None:
        inv.avg_cost = round(payload.avg_cost, 4)
        inv.updated_at = utcnow()
        await db.flush()
        await db.refresh(inv)

    if payload.low_stock_threshold is not None:
        inv = await svc.update_threshold(item_name, payload.low_stock_threshold)

    if payload.unit is not None:
        inv.unit = normalize_unit_name(payload.unit)
        inv.updated_at = utcnow()
        await db.flush()
        await db.refresh(inv)

    if payload.sale_price_amount is not None:
        inv.sale_price_amount = payload.sale_price_amount
    if payload.sale_price_quantity is not None:
        inv.sale_price_quantity = payload.sale_price_quantity
    if payload.sale_currency is not None:
        inv.sale_currency = normalize_currency_code(payload.sale_currency)
    if any(
        value is not None
        for value in (payload.sale_price_amount, payload.sale_price_quantity, payload.sale_currency)
    ):
        inv.updated_at = utcnow()
        await db.flush()
        await db.refresh(inv)

    return InventoryOut.model_validate(inv)


@router.delete("/{item_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_item(
    item_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete an inventory record entirely from the database."""
    svc = InventoryService(db)
    deleted = await svc.delete_item(item_name)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No inventory record found for '{item_name}'.",
        )
    return None



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
