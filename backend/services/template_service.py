"""
Susu Books - Template Service
Loads and fills multilingual response templates.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TemplateService:
    """Loads and fills multilingual response templates."""

    def __init__(self, templates_dir: str | Path = "templates"):
        base_path = Path(templates_dir)
        if not base_path.is_absolute():
            base_path = Path(__file__).resolve().parent.parent / base_path
        self.templates_dir = base_path
        self.templates: dict[str, dict[str, str]] = {}
        self._load_all()

    def _load_all(self) -> None:
        self.templates.clear()
        for file in sorted(self.templates_dir.glob("*.json")):
            with file.open("r", encoding="utf-8") as handle:
                self.templates[file.stem] = json.load(handle)

    def get_response(
        self,
        template_key: str,
        language: str,
        params: dict[str, Any],
    ) -> str:
        lang_templates = self.templates.get(language, self.templates.get("en", {}))
        template = lang_templates.get(template_key)
        if not template:
            template = self.templates.get("en", {}).get(template_key, "")
        if not template:
            return str(params)

        formatted_params: dict[str, Any] = {}
        for key, value in params.items():
            if isinstance(value, float):
                formatted_params[key] = f"{value:,.2f}" if abs(value) >= 100 else f"{value:.2f}"
            else:
                formatted_params[key] = value

        try:
            return template.format(**formatted_params)
        except KeyError:
            return template

    def choose_template_key(self, function_name: str, result: dict[str, Any]) -> str:
        if function_name == "record_purchase":
            return "purchase_confirmed_with_supplier" if result.get("supplier") else "purchase_confirmed"

        if function_name == "record_sale":
            if result.get("out_of_stock"):
                return "sale_out_of_stock"
            if result.get("low_stock_warning"):
                return "sale_low_stock_warning"
            return "sale_confirmed"

        if function_name == "record_expense":
            return "expense_confirmed"

        if function_name == "check_inventory":
            items = result.get("items") or []
            if len(items) != 1:
                return "inventory_all_header"

            status = items[0].get("status")
            if status == "out":
                return "inventory_out"
            if status == "low":
                return "inventory_low"
            return "inventory_single"

        if function_name == "daily_summary":
            return "daily_summary"

        if function_name == "weekly_report":
            return "weekly_report"

        if function_name == "export_credit_profile":
            return "credit_profile"

        if function_name == "clarify_input":
            if str(result.get("reason", "")).strip().lower() == "welcome":
                return "welcome"
            if str(result.get("reason", "")).strip().lower() in {
                "image_unclear",
                "no_transactions_found",
                "no_clear_transaction",
            }:
                return "photo_unclear"
            return "clarify"

        return "error"

    def render_inventory_list(self, language: str, items: list[dict[str, Any]]) -> str:
        if not items:
            return self.get_response("inventory_empty", language, {})

        header = self.get_response("inventory_all_header", language, {})
        lines = [
            self.get_response(
                "inventory_item_line",
                language,
                {
                    "item": item.get("item", ""),
                    "quantity": item.get("quantity", 0),
                    "unit": item.get("unit", ""),
                    "status": item.get("status", "ok"),
                },
            )
            for item in items
        ]
        return "\n".join([header, *lines])
