"""
Susu Books - Pydantic Schemas
Request/response models for all API endpoints and internal service contracts.
"""

from datetime import datetime, date
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator
from enum import Enum


ITEM_ALIASES: dict[str, str] = {
    "shinkafa": "rice",
    "mchele": "rice",
    "rice": "rice",
    "gyeene": "onions",
    "gyene": "onions",
    "onion": "onions",
    "onions": "onions",
    "nkwan": "palm oil",
    "palm_oil": "palm oil",
    "palm oil": "palm oil",
    "tamatis": "tomatoes",
    "tomato": "tomatoes",
    "tomatoes": "tomatoes",
    "borɔdeɛ": "plantains",
    "borodeɛ": "plantains",
    "plantain": "plantains",
    "plantains": "plantains",
    "awɛ": "beans",
    "awe": "beans",
    "bean": "beans",
    "beans": "beans",
    "nam": "fish",
    "fish": "fish",
    "asikire": "sugar",
    "sugar": "sugar",
    "flawa": "flour",
    "flour": "flour",
    "nkyene": "salt",
    "salt": "salt",
    "bayerɛ": "yams",
    "bayere": "yams",
    "yam": "yams",
    "yams": "yams",
    "bankye": "cassava",
    "cassava": "cassava",
    "nkateɛ": "groundnuts",
    "nkatee": "groundnuts",
    "groundnut": "groundnuts",
    "groundnuts": "groundnuts",
    "mako": "pepper",
    "pepper": "pepper",
    "gari": "gari",
    "kenkey": "kenkey",
    "banku": "banku",
}

UNIT_ALIASES: dict[str, str] = {
    "bag": "bags",
    "bags": "bags",
    "crate": "crates",
    "crates": "crates",
    "piece": "pieces",
    "pieces": "pieces",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "liter": "liters",
    "litre": "liters",
    "litres": "liters",
    "liters": "liters",
    "bunch": "bunches",
    "bunches": "bunches",
    "tuber": "tubers",
    "tubers": "tubers",
    "basket": "baskets",
    "baskets": "baskets",
    "tin": "tins",
    "tins": "tins",
    "bowl": "bowls",
    "bowls": "bowls",
    "carton": "cartons",
    "cartons": "cartons",
    "magunia": "bags",
    "gunia": "bags",
}

CURRENCY_ALIASES: dict[str, str] = {
    "ghs": "GHS",
    "cedi": "GHS",
    "cedis": "GHS",
    "ghana cedi": "GHS",
    "ghana cedis": "GHS",
    "ngn": "NGN",
    "naira": "NGN",
    "nairas": "NGN",
    "kes": "KES",
    "shilling": "KES",
    "shillings": "KES",
    "kenyan shilling": "KES",
    "kenyan shillings": "KES",
    "xof": "XOF",
    "cfa": "XOF",
    "franc": "XOF",
    "francs": "XOF",
}


def normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def normalize_item_name(value: str) -> str:
    normalized = normalize_text(value).lower().replace("-", " ").replace("_", " ")
    return ITEM_ALIASES.get(normalized, normalized)


def normalize_unit_name(value: str) -> str:
    normalized = normalize_text(value).lower()
    return UNIT_ALIASES.get(normalized, normalized)


def normalize_currency_code(value: Any) -> str:
    if not value:
        return "GHS"
    normalized = normalize_text(str(value)).lower()
    return CURRENCY_ALIASES.get(normalized, normalized.upper() or "GHS")


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


class ExpenseCategory(str, Enum):
    transport = "transport"
    rent = "rent"
    utilities = "utilities"
    food = "food"
    phone = "phone"
    supplies = "supplies"
    staff = "staff"
    market_fee = "market_fee"
    other = "other"


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
    source: TransactionSource = TransactionSource.manual


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
    last_sale_price: Optional[float]
    low_stock_threshold: float
    is_low_stock: bool
    created_at: datetime
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
    top_selling_quantity: Optional[float]
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
    language: str = "en"
    language_detected: Optional[str] = None


class ImageChatResponse(BaseModel):
    response: str
    transactions: list[TransactionOut] = Field(default_factory=list)
    function_calls: list[FunctionCallRecord] = Field(default_factory=list)
    language: str = "en"
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
    top_selling_quantity: Optional[float]
    profit_change_pct: Optional[float]
    currency: str = "GHS"
    profit_margin_pct: Optional[float]
    comparison_to_yesterday: Optional[dict[str, Any]]


class WeeklyReportResponse(BaseModel):
    period_start: str
    period_end: str
    currency: str = "GHS"
    start_date: str
    end_date: str
    total_revenue: float
    total_cost: float
    total_expenses: float
    total_profit: float
    avg_daily_profit: float
    total_transactions: int
    best_day: Optional[dict[str, Any]]
    worst_day: Optional[dict[str, Any]]
    daily_profits: list[float]
    top_items: list[dict[str, Any]]
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
    active_days: int
    consistency_score: float
    top_categories: list[dict[str, Any]]
    monthly_breakdown: list[dict[str, Any]]
    risk_level: str  # 'low' | 'medium' | 'high'


class LanguageInfo(BaseModel):
    code: str
    name: str
    native_name: str


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

    @field_validator("supplier", "notes", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("item", mode="before")
    @classmethod
    def _normalize_item(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("item is required")
        return normalize_item_name(value)

    @field_validator("unit", mode="before")
    @classmethod
    def _normalize_unit(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("unit is required")
        return normalize_unit_name(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> str:
        return normalize_currency_code(value)


class RecordSaleArgs(BaseModel):
    item: str
    quantity: float = Field(..., gt=0)
    sale_price: float = Field(..., gt=0)
    unit: str
    customer: Optional[str] = None
    currency: str = "GHS"
    notes: Optional[str] = None

    @field_validator("customer", "notes", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("item", mode="before")
    @classmethod
    def _normalize_item(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("item is required")
        return normalize_item_name(value)

    @field_validator("unit", mode="before")
    @classmethod
    def _normalize_unit(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("unit is required")
        return normalize_unit_name(value)

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> str:
        return normalize_currency_code(value)


class RecordExpenseArgs(BaseModel):
    category: ExpenseCategory
    amount: float = Field(..., gt=0)
    description: str
    currency: str = "GHS"
    notes: Optional[str] = None

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, value: Any) -> str:
        if not value:
            return ExpenseCategory.other.value

        normalized = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "market": "market_fee",
            "market_dues": "market_fee",
            "market_charge": "market_fee",
            "market_stall_fee": "market_fee",
            "stall_fee": "market_fee",
            "fees": "other",
            "wages": "staff",
            "salary": "staff",
            "salaries": "staff",
            "airtime": "phone",
            "credit": "phone",
            "electricity": "utilities",
            "water": "utilities",
            "materials": "supplies",
            "stock_supplies": "supplies",
        }
        return aliases.get(normalized, normalized)

    @field_validator("description", "notes", mode="before")
    @classmethod
    def _strip_description(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, value: Any) -> str:
        return normalize_currency_code(value)


class CheckInventoryArgs(BaseModel):
    item: Optional[str] = None

    @field_validator("item", mode="before")
    @classmethod
    def _strip_item(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return normalize_item_name(value) if value else None
        return value


class DailySummaryArgs(BaseModel):
    date: Optional[str] = Field(
        None,
        pattern=r"^\d{4}-\d{2}-\d{2}$"
    )


class WeeklyReportArgs(BaseModel):
    pass


class ExportCreditProfileArgs(BaseModel):
    days: int = Field(default=180, gt=0, le=730)


class ClarifyInputArgs(BaseModel):
    reason: str = Field(default="unclear_input", max_length=255)

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_text(cls, value: Any) -> Any:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value
