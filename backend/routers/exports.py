"""
Susu Books - Export Router
CSV and JSON backup exports for ledger portability and recovery.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, date as date_type, datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_db
from models import DailySummary, Inventory
from schemas import TransactionType
from services.ledger_service import LedgerService

router = APIRouter(prefix="/api/export", tags=["exports"])
settings = get_settings()


@router.get("/transactions.csv")
async def export_transactions_csv(
    date: Optional[str] = Query(
        None,
        description="Optional date filter in YYYY-MM-DD format.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    type: Optional[TransactionType] = Query(None, description="Optional transaction type filter."),
    db: AsyncSession = Depends(get_db),
):
    """Export transactions as a CSV file for spreadsheets or backups."""
    parsed_date: Optional[date_type] = None
    if date:
        try:
            parsed_date = date_type.fromisoformat(date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format: {date}. Use YYYY-MM-DD.",
            ) from exc

    ledger = LedgerService(db)
    transactions = await ledger.get_transactions(
        transaction_date=parsed_date,
        transaction_type=type.value if type else None,
        limit=settings.export_max_rows,
        offset=0,
    )

    csv_buffer = StringIO()
    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=[
            "id",
            "type",
            "item",
            "quantity",
            "unit",
            "unit_price",
            "total_amount",
            "currency",
            "counterparty",
            "category",
            "notes",
            "source",
            "language",
            "confidence",
            "created_at",
            "updated_at",
        ],
    )
    writer.writeheader()
    for transaction in reversed(transactions):
        writer.writerow(
            {
                "id": transaction.id,
                "type": transaction.type,
                "item": transaction.item,
                "quantity": transaction.quantity,
                "unit": transaction.unit,
                "unit_price": transaction.unit_price,
                "total_amount": transaction.total_amount,
                "currency": transaction.currency,
                "counterparty": transaction.counterparty,
                "category": transaction.category,
                "notes": transaction.notes,
                "source": transaction.source,
                "language": transaction.language,
                "confidence": transaction.confidence,
                "created_at": transaction.created_at.isoformat() if transaction.created_at else None,
                "updated_at": transaction.updated_at.isoformat() if transaction.updated_at else None,
            }
        )

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=csv_buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="susu-books-transactions-{stamp}.csv"'
        },
    )


@router.get("/backup.json")
async def export_backup_json(
    include_audit_trail: bool = Query(
        False,
        description="Include raw_input audit text in exported transactions.",
    ),
    db: AsyncSession = Depends(get_db),
):
    """Export a portable JSON snapshot of the ledger, inventory, and summaries."""
    ledger = LedgerService(db)
    transactions = await ledger.get_transactions(limit=settings.export_max_rows, offset=0)

    inventory_result = await db.execute(
        select(Inventory).order_by(Inventory.item.asc())
    )
    inventory_rows = list(inventory_result.scalars().all())

    summaries_result = await db.execute(
        select(DailySummary).order_by(DailySummary.date.asc())
    )
    summary_rows = list(summaries_result.scalars().all())

    transaction_payload = []
    for transaction in reversed(transactions):
        record = transaction.to_dict()
        if not include_audit_trail:
            record.pop("raw_input", None)
        transaction_payload.append(record)

    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "counts": {
            "transactions": len(transaction_payload),
            "inventory_items": len(inventory_rows),
            "daily_summaries": len(summary_rows),
        },
        "transactions": transaction_payload,
        "inventory": [row.to_dict() for row in inventory_rows],
        "daily_summaries": [row.to_dict() for row in summary_rows],
    }

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    return Response(
        content=json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="susu-books-backup-{stamp}.json"'
        },
    )
