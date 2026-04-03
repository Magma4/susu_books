"""
Susu Books - SQLAlchemy ORM Models
Defines the three core tables: transactions, inventory, daily_summaries.
"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import (
    Integer, Float, String, Text, DateTime, Date, Boolean,
    func, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Transaction(Base):
    """
    Represents a single financial event: purchase, sale, or expense.
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Core classification
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Values: 'purchase' | 'sale' | 'expense'

    # Item / product details
    item: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_amount: Mapped[float] = mapped_column(Float, nullable=False)

    # Financial metadata
    currency: Mapped[str] = mapped_column(String(10), default="GHS", nullable=False)
    counterparty: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # For purchases: supplier name; for sales: customer name

    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # For expenses: transport, rent, utilities, staff, etc.

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Input provenance
    source: Mapped[str] = mapped_column(String(20), default="voice", nullable=False)
    # Values: 'voice' | 'photo' | 'manual'

    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    raw_input: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "item": self.item,
            "quantity": self.quantity,
            "unit": self.unit,
            "unit_price": self.unit_price,
            "total_amount": self.total_amount,
            "currency": self.currency,
            "counterparty": self.counterparty,
            "category": self.category,
            "notes": self.notes,
            "source": self.source,
            "language": self.language,
            "raw_input": self.raw_input,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Inventory(Base):
    """
    Tracks current stock levels and cost basis for each item.
    Uses a weighted average cost method for avg_cost.
    """
    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    quantity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Cost tracking
    avg_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_purchase_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Alerting
    low_stock_threshold: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    is_low_stock: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item": self.item,
            "quantity": self.quantity,
            "unit": self.unit,
            "avg_cost": self.avg_cost,
            "last_purchase_price": self.last_purchase_price,
            "low_stock_threshold": self.low_stock_threshold,
            "is_low_stock": self.is_low_stock,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DailySummary(Base):
    """
    Pre-computed (or lazily computed) daily financial summaries.
    One row per calendar date.
    """
    __tablename__ = "daily_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)

    total_revenue: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_expenses: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    net_profit: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    top_selling_item: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "total_revenue": self.total_revenue,
            "total_cost": self.total_cost,
            "total_expenses": self.total_expenses,
            "net_profit": self.net_profit,
            "transaction_count": self.transaction_count,
            "top_selling_item": self.top_selling_item,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
        }
