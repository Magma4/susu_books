"""
Susu Books - Pydantic Schemas
Request/response models for all API endpoints and internal service contracts.
"""

from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransactionType(str, Enum):
    purchase = "purchase"
    sale = "sale"
    expense = "expense"


class TransactionSource(str, Enum):
    voice = "voice"
    photo = "photo"
    manual = "manual"


# ---------------------------------------------------------------------------
# Transaction Schemas
# ---------------------------------------------------------------------------

class TransactionBase(BaseModel):
    type: TransactionType
    item: str = Field(..., min_length=1, max_length=255)
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=50)
    unit_price: Optional[float] = Field(None, gt=0)
    total_amount: float = Field(..., gt=0)
    currency: str = Field(default="GHS", max_length=10)
    counterparty: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    source: TransactionSource = TransactionSource.voice
    language: str = Field(default="en", max_length=10)
    raw_input: Optional[str] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    item: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    unit_price: Optional[float] = Field(None, gt=0)
    total_amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = None
    counterparty: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class TransactionOut(TransactionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Inventory Schemas
# ---------------------------------------------------------------------------

class InventoryOut(BaseModel):
    id: int
    item: str
    quantity: float
    unit: Optional[str]
    avg_cost: Optional[float]
    last_purchase_price: Optional[float]
    low_stock_threshold: float
    is_low_stock: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class InventoryUpdate(BaseModel):
    low_stock_threshold: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None


# ---------------------------------------------------------------------------
# Daily Summary Schema
# ---------------------------------------------------------------------------

class DailySummaryOut(BaseModel):
    id: int
    date: date
    total_revenue: float
    total_cost: float
    total_expenses: float
    net_profit: float
    transaction_count: int
    top_selling_item: Optional[str]
    generated_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# AI / Chat Schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="en", max_length=10)
    conversation_history: list[dict[str, str]] = Field(
        default_factory=list,
        description="Previous messages in the conversation for context"
    )


class FunctionCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: Optional[dict[str, Any]] = None
    success: bool = True
    error: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    transactions: list[TransactionOut] = Field(default_factory=list)
    function_calls: list[FunctionCallRecord] = Field(default_factory=list)
    language_detected: Optional[str] = None


class ImageChatResponse(BaseModel):
    response: str
    transactions: list[TransactionOut] = Field(default_factory=list)
    function_calls: list[FunctionCallRecord] = Field(default_factory=list)
    raw_ocr_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Report Schemas
# ---------------------------------------------------------------------------

class DailyReportRequest(BaseModel):
    date: Optional[str] = Field(
        None,
        description="Date in YYYY-MM-DD format. Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )


class DailySummaryResponse(BaseModel):
    date: str
    total_revenue: float
    total_cost: float
    total_expenses: float
    net_profit: float
    transaction_count: int
    top_selling_item: Optional[str]
    profit_margin_pct: Optional[float]
    comparison_to_yesterday: Optional[dict[str, Any]]


class WeeklyReportResponse(BaseModel):
    start_date: str
    end_date: str
    total_revenue: float
    total_cost: float
    total_expenses: float
    total_profit: float
    avg_daily_profit: float
    best_day: Optional[dict[str, Any]]
    worst_day: Optional[dict[str, Any]]
    daily_trend: list[dict[str, Any]]
    top_items_by_revenue: list[dict[str, Any]]


class CreditProfileResponse(BaseModel):
    generated_at: str
    period_days: int
    avg_daily_revenue: float
    avg_daily_profit: float
    total_revenue: float
    total_profit: float
    total_transactions: int
    consistency_score: float = Field(
        ...,
        description="0-100 score: how consistently the business generates daily revenue"
    )
    top_categories: list[dict[str, Any]]
    monthly_breakdown: list[dict[str, Any]]
    risk_level: str  # 'low' | 'medium' | 'high'


# ---------------------------------------------------------------------------
# Gemma Function Call Payloads (used internally by gemma_service)
# ---------------------------------------------------------------------------

class RecordPurchaseArgs(BaseModel):
    item: str
    quantity: float = Field(..., gt=0)
    unit_price: float = Field(..., gt=0)
    unit: str
    supplier: Optional[str] = None
    currency: str = "GHS"
    notes: Optional[str] = None


class RecordSaleArgs(BaseModel):
    item: str
    quantity: float = Field(..., gt=0)
    sale_price: float = Field(..., gt=0)
    unit: str
    customer: Optional[str] = None
    currency: str = "GHS"
    notes: Optional[str] = None


class RecordExpenseArgs(BaseModel):
    category: str
    amount: float = Field(..., gt=0)
    description: str
    currency: str = "GHS"
    notes: Optional[str] = None


class CheckInventoryArgs(BaseModel):
    item: Optional[str] = None


class DailySummaryArgs(BaseModel):
    date: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )


class WeeklyReportArgs(BaseModel):
    pass


class ExportCreditProfileArgs(BaseModel):
    days: int = Field(default=180, gt=0, le=730)
