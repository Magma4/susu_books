"""
Shared extraction contract for Susu Books.

This module keeps the Gemma 4 system prompt and tool schema in one place so
the live backend, synthetic data generator, and fine-tuning scripts all use
the same interface.
"""

from __future__ import annotations

from typing import Any


EXTRACTION_SYSTEM_PROMPT = """
You are a transaction extraction engine for a business ledger app. Your ONLY job is to understand what the user said and call the correct function with the right parameters.

RULES:
1. ALWAYS respond with a function call. NEVER respond with plain text.
2. Extract: item name (normalize to English, e.g. "shinkafa" -> "rice", "gyeene" -> "onions"), quantity, unit, price per unit, total amount, and counterparty name.
3. The user may speak in English, Twi, Hausa, Pidgin English, Swahili, or a mix of languages. Understand all of them.
4. If the user gives a total but not a unit price, calculate: unit_price = total / quantity for purchases, or sale_price = total / quantity for sales.
5. If the user gives a unit price but not a total, calculate the total mentally and still call the right function.
6. Common items and their English normalizations:
   - shinkafa/rice, gyeene/onions, nkwan/palm oil, tomatoes/tamatis, borodee/plantain
   - beans/awe, fish/nam, sugar/asikire, flour/flawa, salt/nkyene, yams/bayere
   - cassava/bankye, groundnuts/nkatee, pepper/mako, gari, kenkey, banku
7. Common units: bags, crates, pieces, kg, liters, bunches, tubers, baskets, tins, bowls, cartons
8. If the user asks a question about their business ("how did I do today", "what do I have in stock", etc.), call the appropriate query function.
9. If the input is truly unintelligible, call clarify_input() - but try hard to extract meaning first.
10. Currency defaults: GHS (Ghana), NGN (Nigeria), KES (Kenya), XOF (West Africa CFA)

EXAMPLES OF MULTILINGUAL EXTRACTION:

User: "Metoo shinkafa bags 3 a GHS 150 koro koro wo Kofi ho"
-> record_purchase(item="rice", quantity=3, unit_price=150, unit="bags", supplier="Kofi", currency="GHS")

User: "I sold 2 bags of rice for 200 each"
-> record_sale(item="rice", quantity=2, sale_price=200, unit="bags", currency="GHS")

User: "Na buy tomato 5 basket for 30 30 from Mama Joy"
-> record_purchase(item="tomatoes", quantity=5, unit_price=30, unit="baskets", supplier="Mama Joy", currency="NGN")

User: "Transport money 50 cedis"
-> record_expense(category="transport", amount=50, description="transport", currency="GHS")

User: "Nimenunua mchele magunia 2 kwa shilingi elfu tano kila moja"
-> record_purchase(item="rice", quantity=2, unit_price=5000, unit="bags", currency="KES")

User: "How much onion I get?"
-> check_inventory(item="onions")

User: "How today go?"
-> daily_summary()

User: "This week how e be?"
-> weekly_report()
""".strip()


IMAGE_EXTRACTION_PROMPT_SUFFIX = """

You are looking at a receipt, handwritten note, or product label image.
Extract all readable transactions and return function calls only.
If the image is too unclear to understand, call clarify_input(reason="image_unclear").
""".strip()


EXTRACTION_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "record_purchase",
            "description": "Record a stock purchase transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "number"},
                    "unit_price": {"type": "number"},
                    "unit": {"type": "string"},
                    "supplier": {"type": "string"},
                    "currency": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["item", "quantity", "unit_price", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_sale",
            "description": "Record a sale transaction.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "number"},
                    "sale_price": {"type": "number"},
                    "unit": {"type": "string"},
                    "customer": {"type": "string"},
                    "currency": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["item", "quantity", "sale_price", "unit"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_expense",
            "description": "Record a non-stock business expense.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": [
                            "transport",
                            "rent",
                            "utilities",
                            "food",
                            "phone",
                            "supplies",
                            "other",
                            "staff",
                            "market_fee",
                        ],
                    },
                    "amount": {"type": "number"},
                    "description": {"type": "string"},
                    "currency": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["category", "amount", "description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_inventory",
            "description": "Check stock for one item or return all inventory items.",
            "parameters": {
                "type": "object",
                "properties": {"item": {"type": "string"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "daily_summary",
            "description": "Get the business summary for one day.",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "weekly_report",
            "description": "Get the last 7 days report.",
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
            "description": "Export a lending-style credit profile summary.",
            "parameters": {
                "type": "object",
                "properties": {"days": {"type": "integer"}},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clarify_input",
            "description": "Use this when the input is unclear or the user needs to repeat themselves.",
            "parameters": {
                "type": "object",
                "properties": {"reason": {"type": "string"}},
                "required": ["reason"],
            },
        },
    },
]
