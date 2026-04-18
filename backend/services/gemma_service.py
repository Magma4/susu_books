"""
Susu Books - Gemma 4 extraction service
Gemma runs locally through Ollama and returns function calls only.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import date
from typing import Any, Optional

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_contract import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_TOOLS,
    IMAGE_EXTRACTION_PROMPT_SUFFIX,
)
from config import get_settings
from schemas import (
    ChatResponse,
    CheckInventoryArgs,
    ClarifyInputArgs,
    DailySummaryArgs,
    ExportCreditProfileArgs,
    FunctionCallRecord,
    ImageChatResponse,
    LanguageInfo,
    RecordExpenseArgs,
    RecordPurchaseArgs,
    RecordSaleArgs,
    TransactionOut,
    TransactionSource,
    normalize_currency_code,
)
from services.inventory_service import InventoryService
from services.ledger_service import LedgerService
from services.report_service import ReportService
from services.template_service import TemplateService

logger = logging.getLogger(__name__)
settings = get_settings()


AVAILABLE_LANGUAGES: list[LanguageInfo] = [
    LanguageInfo(code="en", name="English", native_name="English"),
    LanguageInfo(code="tw", name="Twi", native_name="Twi"),
    LanguageInfo(code="ha", name="Hausa", native_name="Hausa"),
    LanguageInfo(code="pcm", name="Pidgin English", native_name="Pidgin"),
    LanguageInfo(code="sw", name="Swahili", native_name="Kiswahili"),
]


SYSTEM_PROMPT = EXTRACTION_SYSTEM_PROMPT
IMAGE_PROMPT_SUFFIX = IMAGE_EXTRACTION_PROMPT_SUFFIX
TOOLS: list[dict[str, Any]] = EXTRACTION_TOOLS


class GemmaService:
    """Coordinates Ollama tool-calling and deterministic template rendering."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.ledger = LedgerService(db)
        self.inventory = InventoryService(db)
        self.reports = ReportService(db)
        self.templates = TemplateService("templates")
        self.client = httpx.AsyncClient(
            base_url=settings.ollama_base_url,
            timeout=httpx.Timeout(settings.ollama_timeout),
        )
        self._resolved_model_name: Optional[str] = None

    async def close(self) -> None:
        await self.client.aclose()

    async def chat(
        self,
        message: str,
        language: str = "en",
        conversation_history: Optional[list[dict[str, str]]] = None,
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord]]:
        messages = self._build_messages(
            message=message,
            history=conversation_history,
            system_prompt=SYSTEM_PROMPT.strip(),
        )
        return await self._extract_and_execute(
            messages=messages,
            language=language,
            source=TransactionSource.voice,
            raw_input=message,
        )

    async def chat_with_image(
        self,
        image_bytes: bytes,
        text_prompt: str = "What transactions can you see in this image?",
        language: str = "en",
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord], Optional[str]]:
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {"role": "system", "content": (SYSTEM_PROMPT + IMAGE_PROMPT_SUFFIX).strip()},
            {
                "role": "user",
                "content": text_prompt,
                "images": [encoded_image],
            },
        ]

        response_text, transactions, function_calls = await self._extract_and_execute(
            messages=messages,
            language=language,
            source=TransactionSource.photo,
            raw_input=text_prompt or "[image upload]",
        )
        return response_text, transactions, function_calls, None

    async def _extract_and_execute(
        self,
        messages: list[dict[str, Any]],
        language: str,
        source: TransactionSource,
        raw_input: str,
    ) -> tuple[str, list[TransactionOut], list[FunctionCallRecord]]:
        assistant_message = await self._run_extraction_pass(messages)
        tool_calls = self._extract_tool_calls(assistant_message)

        if not tool_calls:
            clarify = FunctionCallRecord(
                name="clarify_input",
                arguments={"reason": "image_unclear" if source == TransactionSource.photo else "unclear_input"},
                result={"reason": "image_unclear" if source == TransactionSource.photo else "unclear_input"},
                success=True,
            )
            response_text = self._render_response(language, [clarify])
            return response_text, [], [clarify]

        transactions: list[TransactionOut] = []
        call_log: list[FunctionCallRecord] = []

        for raw_call in tool_calls:
            function_name = str(raw_call.get("function", {}).get("name", "")).strip()
            raw_arguments = raw_call.get("function", {}).get("arguments", {})
            arguments = self._massage_arguments(function_name, self._parse_arguments(raw_arguments))

            record = FunctionCallRecord(name=function_name, arguments=arguments)
            try:
                result, transaction = await self._execute_function(
                    name=function_name,
                    args=arguments,
                    language=language,
                    source=source,
                    raw_input=raw_input,
                )
                record.result = result
                record.success = True
                if transaction is not None:
                    transactions.append(transaction)
            except ValidationError as exc:
                await self.db.rollback()
                logger.info("Validation error for %s: %s", function_name, exc)
                record.result = {"reason": "unclear_input"}
                record.success = False
                record.error = "Invalid or incomplete arguments."
            except Exception as exc:
                await self.db.rollback()
                logger.exception("Tool execution error for %s: %s", function_name, exc)
                record.result = {"reason": "unclear_input"}
                record.success = False
                record.error = str(exc)

            call_log.append(record)

        response_text = self._render_response(language, call_log)
        return response_text, transactions, call_log

    async def _run_extraction_pass(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        model_name = await self._resolve_model_name()
        payload = {
            "model": model_name,
            "messages": messages,
            "tools": TOOLS,
            "stream": False,
            "options": {
                "temperature": settings.ai_temperature,
                "top_p": settings.ai_top_p,
                "top_k": settings.ai_top_k,
            },
        }

        last_error: Exception | None = None
        for attempt in range(settings.ollama_max_retries):
            try:
                response = await self.client.post("/api/chat", json=payload)
                response.raise_for_status()
                message = response.json().get("message", {})
                if self._extract_tool_calls(message):
                    return message
                if attempt < settings.ollama_max_retries - 1:
                    retry_messages = list(messages)
                    retry_messages.append(
                        {
                            "role": "user",
                            "content": "Return a function call only. Do not answer in plain text.",
                        }
                    )
                    payload["messages"] = retry_messages
                else:
                    return message
            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                last_error = exc
                logger.warning("Ollama request attempt %d failed: %s", attempt + 1, exc)

        if last_error is not None:
            raise last_error
        raise RuntimeError("Ollama request failed without a specific exception.")

    async def _execute_function(
        self,
        name: str,
        args: dict[str, Any],
        language: str,
        source: TransactionSource,
        raw_input: str,
    ) -> tuple[dict[str, Any], Optional[TransactionOut]]:
        transaction: Optional[TransactionOut] = None

        if name == "record_purchase":
            parsed = RecordPurchaseArgs(**args)
            result = await self.ledger.record_purchase(parsed, language=language, source=source, raw_input=raw_input)
            transaction = await self._fetch_transaction(int(result["transaction_id"]))
            return result, transaction

        if name == "record_sale":
            parsed = RecordSaleArgs(**args)
            result = await self.ledger.record_sale(parsed, language=language, source=source, raw_input=raw_input)
            transaction = await self._fetch_transaction(int(result["transaction_id"]))
            return result, transaction

        if name == "record_expense":
            parsed = RecordExpenseArgs(**args)
            result = await self.ledger.record_expense(parsed, language=language, source=source, raw_input=raw_input)
            transaction = await self._fetch_transaction(int(result["transaction_id"]))
            return result, transaction

        if name == "check_inventory":
            parsed = CheckInventoryArgs(**args)
            return await self.inventory.check_inventory(parsed.item), None

        if name == "daily_summary":
            parsed = DailySummaryArgs(**args)
            target_date = date.fromisoformat(parsed.date) if parsed.date else None
            return await self.reports.daily_summary(target_date), None

        if name == "weekly_report":
            return await self.reports.weekly_report(), None

        if name == "export_credit_profile":
            parsed = ExportCreditProfileArgs(**args)
            return await self.reports.export_credit_profile(parsed.days), None

        if name == "clarify_input":
            parsed = ClarifyInputArgs(**args)
            return {"reason": parsed.reason or "unclear_input"}, None

        raise ValueError(f"Unknown function: {name}")

    def _render_response(self, language: str, function_calls: list[FunctionCallRecord]) -> str:
        rendered_parts: list[str] = []
        for call in function_calls:
            result = call.result or {"reason": "unclear_input"}
            template_key = self.templates.choose_template_key(call.name, result)

            if call.name == "check_inventory" and len(result.get("items", [])) != 1:
                rendered_parts.append(self.templates.render_inventory_list(language, list(result.get("items", []))))
                continue

            params = self._template_params(call.name, result)
            rendered_parts.append(self.templates.get_response(template_key, language, params))

            if call.name == "daily_summary" and result.get("profit_change_pct") is not None:
                comparison_key = (
                    "daily_summary_comparison_up"
                    if float(result["profit_change_pct"]) >= 0
                    else "daily_summary_comparison_down"
                )
                rendered_parts.append(
                    self.templates.get_response(
                        comparison_key,
                        language,
                        {"profit_change_pct": abs(float(result["profit_change_pct"]))},
                    )
                )

        return "\n".join(part for part in rendered_parts if part).strip() or self.templates.get_response("error", language, {})

    def _template_params(self, function_name: str, result: dict[str, Any]) -> dict[str, Any]:
        if function_name == "record_purchase":
            return {
                "item": result.get("item", ""),
                "quantity": result.get("quantity", 0),
                "unit": result.get("unit", ""),
                "currency": result.get("currency", "GHS"),
                "total_amount": result.get("total_amount", 0),
                "new_stock_level": result.get("new_stock_level", 0),
                "supplier": result.get("supplier", ""),
            }

        if function_name == "record_sale":
            return {
                "item": result.get("item", ""),
                "quantity": result.get("quantity", 0),
                "unit": result.get("unit", ""),
                "currency": result.get("currency", "GHS"),
                "total_amount": result.get("total_amount", 0),
                "profit": result.get("profit", 0),
                "remaining_stock": result.get("remaining_stock", 0),
            }

        if function_name == "record_expense":
            return {
                "category": str(result.get("category", "")).replace("_", " "),
                "amount": result.get("amount", 0),
                "currency": result.get("currency", "GHS"),
                "total_expenses_today": result.get("total_expenses_today", 0),
            }

        if function_name == "check_inventory":
            item_payload = (result.get("items") or [{}])[0]
            return {
                "item": item_payload.get("item", result.get("item", "")),
                "quantity": item_payload.get("quantity", result.get("quantity", 0)),
                "unit": item_payload.get("unit", result.get("unit", "")),
                "currency": "GHS",
                "avg_cost": item_payload.get("avg_cost", result.get("avg_cost", 0)) or 0,
                "status": item_payload.get("status", result.get("status", "ok")),
            }

        if function_name == "daily_summary":
            return {
                "currency": result.get("currency", "GHS"),
                "total_revenue": result.get("total_revenue", 0),
                "total_cost": result.get("total_cost", 0),
                "total_expenses": result.get("total_expenses", 0),
                "net_profit": result.get("net_profit", 0),
                "transaction_count": result.get("transaction_count", 0),
                "top_selling_item": result.get("top_selling_item") or "none",
            }

        if function_name == "weekly_report":
            best_day = result.get("best_day") or {}
            return {
                "currency": result.get("currency", "GHS"),
                "total_profit": result.get("total_profit", 0),
                "avg_daily_profit": result.get("avg_daily_profit", 0),
                "best_day": best_day.get("date", result.get("period_start", "")),
                "total_transactions": result.get("total_transactions", 0),
            }

        if function_name == "export_credit_profile":
            consistency_score = float(result.get("consistency_score", 0))
            if consistency_score <= 1:
                consistency_score *= 100
            return {
                "currency": "GHS",
                "period_days": result.get("period_days", 180),
                "avg_daily_revenue": result.get("avg_daily_revenue", 0),
                "avg_daily_profit": result.get("avg_daily_profit", 0),
                "active_days": result.get("active_days", 0),
                "consistency_score": round(consistency_score, 2),
                "risk_level": result.get("risk_level", "medium"),
            }

        if function_name == "clarify_input":
            return {}

        return result

    def _build_messages(
        self,
        message: str,
        history: Optional[list[dict[str, str]]],
        system_prompt: str,
    ) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        if history:
            for entry in history:
                role = entry.get("role")
                if role in {"user", "assistant"}:
                    messages.append({"role": role, "content": entry.get("content", "")})
        messages.append({"role": "user", "content": message})
        return messages

    @staticmethod
    def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
        tool_calls = message.get("tool_calls", [])
        return tool_calls if isinstance(tool_calls, list) else []

    @staticmethod
    def _parse_arguments(raw_arguments: Any) -> dict[str, Any]:
        if isinstance(raw_arguments, dict):
            return raw_arguments
        if isinstance(raw_arguments, str):
            try:
                parsed = json.loads(raw_arguments)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    def _massage_arguments(self, function_name: str, args: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(args)

        if function_name == "record_purchase":
            if "sale_price" in normalized and "unit_price" not in normalized:
                normalized["unit_price"] = normalized.pop("sale_price")
            if "total_amount" in normalized and normalized.get("quantity") and not normalized.get("unit_price"):
                normalized["unit_price"] = float(normalized["total_amount"]) / float(normalized["quantity"])
            normalized["currency"] = normalize_currency_code(normalized.get("currency"))

        elif function_name == "record_sale":
            if "unit_price" in normalized and "sale_price" not in normalized:
                normalized["sale_price"] = normalized.pop("unit_price")
            if "total_amount" in normalized and normalized.get("quantity") and not normalized.get("sale_price"):
                normalized["sale_price"] = float(normalized["total_amount"]) / float(normalized["quantity"])
            normalized["currency"] = normalize_currency_code(normalized.get("currency"))

        elif function_name == "record_expense":
            normalized["currency"] = normalize_currency_code(normalized.get("currency"))
            if "description" not in normalized and normalized.get("category"):
                normalized["description"] = str(normalized["category"]).replace("_", " ")

        return normalized

    async def _fetch_transaction(self, transaction_id: int) -> Optional[TransactionOut]:
        from sqlalchemy import select
        from models import Transaction

        result = await self.db.execute(select(Transaction).where(Transaction.id == transaction_id))
        transaction = result.scalar_one_or_none()
        if transaction is None:
            return None
        return TransactionOut.model_validate(transaction)

    async def _list_available_models(self) -> list[str]:
        response = await self.client.get("/api/tags", timeout=10.0)
        response.raise_for_status()
        payload = response.json()
        return [model["name"] for model in payload.get("models", []) if "name" in model]

    async def _resolve_model_name(self) -> str:
        if self._resolved_model_name:
            return self._resolved_model_name

        available_models = await self._list_available_models()
        if settings.ollama_model in available_models:
            self._resolved_model_name = settings.ollama_model
            return self._resolved_model_name

        preferred_order = [
            "gemma4:31b-instruct",
            "gemma4:26b-a4b-instruct",
            "gemma4:e2b",
        ]
        for candidate in preferred_order:
            if candidate in available_models:
                self._resolved_model_name = candidate
                logger.warning(
                    "Configured Ollama model %s is not installed. Falling back to %s.",
                    settings.ollama_model,
                    candidate,
                )
                return self._resolved_model_name

        if available_models:
            self._resolved_model_name = available_models[0]
            logger.warning(
                "No preferred Gemma model installed. Falling back to %s.",
                self._resolved_model_name,
            )
            return self._resolved_model_name

        raise RuntimeError(
            "No Ollama models are installed. Pull a Gemma 4 model first, for example: "
            "`ollama pull gemma4:31b-instruct`."
        )

    async def health_check(self) -> dict[str, Any]:
        try:
            available_models = await self._list_available_models()
            target_model = await self._resolve_model_name()
            return {
                "ollama_reachable": True,
                "provider_reachable": True,
                "model_loaded": bool(target_model),
                "available_models": available_models,
                "target_model": target_model,
                "ai_provider": "ollama",
            }
        except Exception as exc:
            return {
                "ollama_reachable": False,
                "provider_reachable": False,
                "model_loaded": False,
                "available_models": [],
                "target_model": settings.ollama_model,
                "ai_provider": "ollama",
                "error": str(exc),
            }
