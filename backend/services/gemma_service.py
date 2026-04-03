"""
Susu Books - Gemma 4 Service
Manages all interaction with Ollama's /api/chat endpoint, including:
  - Sending user messages with tool definitions
  - Parsing tool call responses
  - Executing the corresponding Python functions
  - Sending tool results back to Gemma for natural language confirmation
"""

import json
import logging
import base64
from typing import Optional, Any
from pathlib import Path

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from schemas import (
    FunctionCallRecord, TransactionOut, TransactionSource,
    RecordPurchaseArgs, RecordSaleArgs, RecordExpenseArgs,
    CheckInventoryArgs, DailySummaryArgs, ExportCreditProfileArgs,
)
from services.ledger_service import LedgerService
from services.inventory_service import InventoryService
from services.report_service import ReportService
from models import Transaction

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are Susu Books, a friendly business assistant for market vendors and small business owners. You help them track purchases, sales, expenses, and inventory by understanding their natural speech.

RULES:
1. When the user describes a business transaction, ALWAYS use the appropriate function call. Never just acknowledge — always record it.
2. Extract: item name, quantity, unit (bags, crates, pieces, kg, etc.), price per unit, total amount, and counterparty (supplier or customer name) from the user's speech.
3. If the user asks about their business (inventory, profits, how they're doing), use check_inventory, daily_summary, or weekly_report.
4. Respond in the SAME LANGUAGE the user spoke in. If they spoke Twi, respond in Twi. If English, respond in English.
5. Keep responses SHORT and conversational. You're talking to a busy vendor, not writing an essay.
6. When confirming a transaction, always state: what was recorded, the total amount, and the current stock level if relevant.
7. Use the local currency the user mentions. Default to GHS (Ghana Cedis) if unclear.
8. If the user's input is ambiguous, ask ONE clarifying question. Don't guess wildly.
9. Be warm, encouraging, and respectful. This person is trusting you with their business.

EXAMPLES:
User (Twi): "Metɔɔ shinkafa bags 3 a GHS 150 koro koro wɔ Kofi hɔ"
→ Call: record_purchase(item="rice", quantity=3, unit_price=150, unit="bags", supplier="Kofi", currency="GHS")
→ Response (Twi): "Makyerɛw. Wotɔɔ shinkafa bags 3 GHS 450 nyinaa wɔ Kofi hɔ. Seesei wo stock mu wɔ bags 8."

User: "Sold 2 bags of rice at 200 each"
→ Call: record_sale(item="rice", quantity=2, sale_price=200, unit="bags", currency="GHS")
→ Response: "Recorded. Sold 2 bags of rice for 400 GHS total. You made 100 GHS profit on this sale. 6 bags remaining."

User: "How did I do today?"
→ Call: daily_summary()
→ Response: "Good day! You made 347 GHS in sales, spent 200 GHS on stock, and 20 GHS on transport. Net profit: 127 GHS. Your best seller was rice — 4 bags sold."
"""

IMAGE_SYSTEM_PROMPT = SYSTEM_PROMPT + """

You are also looking at a photo of a receipt, handwritten note, or product label. Extract all transaction information visible: items, quantities, prices, dates, vendor/customer names. Record each transaction you can identify using the appropriate function calls.
"""

# ---------------------------------------------------------------------------
# Tool definitions (Ollama /api/chat "tools" format)
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "record_purchase",
            "description": (
                "Record a purchase/buying transaction. Use when the user says they bought, "
                "purchased, or acquired goods from a supplier."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "Name of the item purchased"},
                    "quantity": {"type": "number", "description": "Number of units purchased"},
                    "unit_price": {"type": "number", "description": "Price per single unit"},
                    "unit": {"type": "string", "description": "Unit of measurement (bags, crates, pieces, kg, liters, etc.)"},
                    "supplier": {"type": "string", "description": "Name of the supplier or seller"},
                    "currency": {"type": "string", "description": "Currency code. Default: GHS"},
                    "notes": {"type": "string", "description": "Any additional notes"},
                },
                "required": ["item", "quantity", "unit_price", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_sale",
            "description": (
                "Record a sale transaction. Use when the user says they sold, gave out "
                "goods in exchange for money, or received payment."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string", "description": "Name of the item sold"},
                    "quantity": {"type": "number", "description": "Number of units sold"},
                    "sale_price": {"type": "number", "description": "Price per single unit sold"},
                    "unit": {"type": "string", "description": "Unit of measurement"},
                    "customer": {"type": "string", "description": "Name of the customer (if known)"},
                    "currency": {"type": "string", "description": "Currency code. Default: GHS"},
                    "notes": {"type": "string", "description": "Any additional notes"},
                },
                "required": ["item", "quantity", "sale_price", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_expense",
            "description": (
                "Record a business expense that is NOT a stock purchase. Use for transport, "
                "rent, utilities, staff wages, market fees, phone credit, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Expense category: transport, rent, utilities, staff, market_fee, phone, food, other",
                    },
                    "amount": {"type": "number", "description": "Total amount of the expense"},
                    "description": {"type": "string", "description": "What the expense was for"},
                    "currency": {"type": "string", "description": "Currency code. Default: GHS"},
                    "notes": {"type": "string", "description": "Any additional notes"},
                },
                "required": ["category", "amount", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": (
                "Check current stock levels. If item is specified, return details for that "
                "item. If not specified, return all items with low-stock alerts."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "string",
                        "description": "Name of item to check. Omit to see all inventory.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daily_summary",
            "description": (
                "Get a summary of today's business performance: revenue, costs, expenses, "
                "profit, and top-selling item. Can also retrieve a specific past date."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Date in YYYY-MM-DD format. Omit for today.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weekly_report",
            "description": (
                "Get a report covering the last 7 days: total profit, best/worst days, "
                "top items by revenue, daily trend."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "export_credit_profile",
            "description": (
                "Generate a financial summary for a creditworthiness assessment. "
                "Shows average daily revenue/profit, consistency score, and monthly breakdown."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Number of past days to include. Default: 180.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# GemmaService
# ---------------------------------------------------------------------------

class GemmaService:
    """
    Orchestrates the full Gemma 4 function-calling loop:
    1. Send user message + tools to Ollama
    2. Parse any tool_calls from the response
    3. Execute each tool call via the appropriate service
    4. Feed results back to Gemma for a natural language reply
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = LedgerService(db)
        self.inventory = InventoryService(db)
        self.reports = ReportService(db)
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(settings.ollama_timeout),
        )

    async def close(self) -> None:
        await self.client.aclose()

    # ------------------------------------------------------------------
    # Primary entry point: process a text message
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        language: str = "en",
        conversation_history: Optional[list[dict]] = None,
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord]]:
        """
        Process a user message through the full Gemma function-calling loop.

        Returns:
            (response_text, recorded_transactions, function_call_log)
        """
        messages = self._build_messages(message, conversation_history)
        return await self._run_function_loop(
            messages=messages,
            language=language,
            source=TransactionSource.voice,
            raw_input=message,
        )

    # ------------------------------------------------------------------
    # Image / OCR entry point
    # ------------------------------------------------------------------

    async def chat_with_image(
        self,
        image_bytes: bytes,
        text_prompt: str = "What transactions can you see in this image?",
        language: str = "en",
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord], str]:
        """
        Process an image (receipt / handwritten note) through the OCR loop.

        Returns:
            (response_text, recorded_transactions, function_call_log, raw_ocr_description)
        """
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        messages = [
            {"role": "system", "content": IMAGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": text_prompt,
                "images": [b64_image],
            },
        ]

        response_text, transactions, fn_calls = await self._run_function_loop(
            messages=messages,
            language=language,
            source=TransactionSource.photo,
            raw_input="[image upload]",
        )
        return response_text, transactions, fn_calls, response_text

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    async def _run_function_loop(
        self,
        messages: list[dict],
        language: str,
        source: TransactionSource,
        raw_input: str,
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord]]:
        """
        Runs the Gemma tool-calling loop:
          1. Call Ollama with tools
          2. If tool_calls present → execute → append result → call Ollama again
          3. Repeat until no more tool calls (max 10 iterations)
        """
        recorded_transactions: list[TransactionOut] = []
        fn_call_log: list[FunctionCallRecord] = []

        for iteration in range(10):
            payload = {
                "model": settings.ollama_model,
                "messages": messages,
                "tools": TOOLS,
                "stream": False,
            }

            try:
                resp = await self.client.post("/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                logger.error("Ollama HTTP error %d: %s", e.response.status_code, e.response.text)
                raise
            except httpx.RequestError as e:
                logger.error("Ollama connection error: %s", e)
                raise

            assistant_message = data.get("message", {})
            tool_calls = assistant_message.get("tool_calls", [])

            if not tool_calls:
                # No more function calls — extract the final text response
                final_text = assistant_message.get("content", "")
                return final_text, recorded_transactions, fn_call_log

            # Append the assistant's tool-call message to history
            messages.append({"role": "assistant", **assistant_message})

            # Execute each tool call
            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                raw_args = tc.get("function", {}).get("arguments", {})

                # arguments may arrive as a JSON string
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        raw_args = {}

                fn_record = FunctionCallRecord(name=fn_name, arguments=raw_args)

                try:
                    result, tx = await self._execute_function(
                        fn_name, raw_args, language, source, raw_input
                    )
                    fn_record.result = result
                    fn_record.success = True
                    if tx is not None:
                        recorded_transactions.append(tx)
                except Exception as exc:
                    logger.exception("Error executing tool %s: %s", fn_name, exc)
                    result = {"error": str(exc)}
                    fn_record.success = False
                    fn_record.error = str(exc)

                fn_call_log.append(fn_record)

                # Feed tool result back into the conversation
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                })

        # Fallback if loop exhausted
        logger.warning("Gemma function loop hit iteration limit")
        return "I processed your request.", recorded_transactions, fn_call_log

    # ------------------------------------------------------------------
    # Function dispatcher
    # ------------------------------------------------------------------

    async def _execute_function(
        self,
        name: str,
        args: dict[str, Any],
        language: str,
        source: TransactionSource,
        raw_input: str,
    ) -> tuple[dict, Optional[TransactionOut]]:
        """
        Dispatch a Gemma function call to the appropriate service method.
        Returns (result_dict, optional_transaction_out).
        """
        tx: Optional[TransactionOut] = None

        if name == "record_purchase":
            parsed = RecordPurchaseArgs(**args)
            result = await self.ledger.record_purchase(
                parsed, language=language, source=source, raw_input=raw_input
            )
            tx = await self._fetch_transaction(result["transaction_id"])

        elif name == "record_sale":
            parsed = RecordSaleArgs(**args)
            result = await self.ledger.record_sale(
                parsed, language=language, source=source, raw_input=raw_input
            )
            tx = await self._fetch_transaction(result["transaction_id"])

        elif name == "record_expense":
            parsed = RecordExpenseArgs(**args)
            result = await self.ledger.record_expense(
                parsed, language=language, source=source, raw_input=raw_input
            )
            tx = await self._fetch_transaction(result["transaction_id"])

        elif name == "check_inventory":
            parsed = CheckInventoryArgs(**args)
            result = await self.inventory.check_inventory(parsed.item)

        elif name == "daily_summary":
            parsed = DailySummaryArgs(**args)
            from datetime import date
            target = (
                date.fromisoformat(parsed.date)
                if parsed.date
                else None
            )
            result = await self.reports.daily_summary(target)

        elif name == "weekly_report":
            result = await self.reports.weekly_report()

        elif name == "export_credit_profile":
            parsed = ExportCreditProfileArgs(**args)
            result = await self.reports.export_credit_profile(parsed.days)

        else:
            logger.warning("Unknown function called by Gemma: %s", name)
            result = {"error": f"Unknown function: {name}"}

        return result, tx

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        user_message: str,
        history: Optional[list[dict]],
    ) -> list[dict]:
        """Construct the messages array for Ollama."""
        messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if history:
            for h in history:
                if h.get("role") in ("user", "assistant"):
                    messages.append({"role": h["role"], "content": h.get("content", "")})
        messages.append({"role": "user", "content": user_message})
        return messages

    async def _fetch_transaction(self, transaction_id: int) -> Optional[TransactionOut]:
        """Fetch a newly created transaction from the DB and serialize it."""
        from sqlalchemy import select
        from models import Transaction as TxModel
        result = await self.db.execute(
            select(TxModel).where(TxModel.id == transaction_id)
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            return None
        return TransactionOut.model_validate(tx)

    async def health_check(self) -> dict:
        """Ping Ollama to verify the model is loaded."""
        try:
            resp = await self.client.get("/api/tags", timeout=10.0)
            resp.raise_for_status()
            tags_data = resp.json()
            models = [m["name"] for m in tags_data.get("models", [])]
            model_loaded = settings.ollama_model in models
            return {
                "ollama_reachable": True,
                "model_loaded": model_loaded,
                "available_models": models,
                "target_model": settings.ollama_model,
            }
        except Exception as exc:
            return {
                "ollama_reachable": False,
                "model_loaded": False,
                "error": str(exc),
                "target_model": settings.ollama_model,
            }
