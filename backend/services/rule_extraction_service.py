"""
Deterministic extraction fallback for common market utterances.

Gemma remains the primary extraction engine. This service catches short,
high-frequency phrases that speech recognition and smaller local models often
miss, especially low-resource language item names and shorthand cash entries.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from schemas import CURRENCY_ALIASES, ITEM_ALIASES, UNIT_ALIASES, normalize_currency_code


@dataclass(frozen=True)
class ParsedItem:
    item: str
    start: int
    end: int


@dataclass(frozen=True)
class ParsedUnit:
    unit: str
    index: int


class RuleExtractionService:
    """Parses demo-critical multilingual transaction phrases without an LLM."""

    ITEM_PHRASES: dict[str, str] = {
        **ITEM_ALIASES,
        "gye ne": "onions",
        "gyeene": "onions",
        "gyene": "onions",
        "j ne": "onions",
        "jene": "onions",
        "gene": "onions",
        "onion": "onions",
        "onions": "onions",
        "palm oil": "palm oil",
        "palm-oil": "palm oil",
        "palm_oil": "palm oil",
        "palm": "palm oil",
        "tomato": "tomatoes",
        "tomatoes": "tomatoes",
        "tamatis": "tomatoes",
        "plantain": "plantains",
        "plantains": "plantains",
        "borode": "plantains",
        "borodee": "plantains",
        "rice": "rice",
        "shinkafa": "rice",
        "mchele": "rice",
    }

    PURCHASE_MARKERS = {
        "buy",
        "bought",
        "purchase",
        "purchased",
        "na buy",
        "i buy",
        "i bought",
        "me to",
        "meto",
        "metoo",
        "metooo",
        "mereto",
        "mere to",
        "me re to",
        "saya",
        "sayo",
        "na saya",
        "nimenunua",
        "nilinunua",
    }
    SALE_MARKERS = {
        "sell",
        "sold",
        "sale",
        "i sell",
        "i sold",
        "meton",
        "me ton",
        "mere ton",
        "me re ton",
        "obi ato",
        "obi atɔ",
        "ye to",
        "yeto",
        "yetoo",
        "yɛ tɔ",
        "yɛtɔ",
        "ato",
        "atɔ",
        "sayar",
        "na sayar",
        "nimeuza",
        "niliuza",
    }
    EXPENSE_MARKERS: dict[str, tuple[str, ...]] = {
        "transport": ("transport", "trotro", "taxi", "fare"),
        "market_fee": ("market fee", "stall fee", "daily market", "dues"),
        "phone": ("airtime", "phone credit", "data bundle", "phone"),
        "food": ("food", "chop money", "lunch"),
        "rent": ("rent",),
        "utilities": ("electricity", "water", "light bill"),
        "supplies": ("supplies", "materials"),
    }

    _NUMBER_RE = re.compile(r"(?<![A-Za-z])(?:\d+(?:\.\d+)?|\.\d+)(?![A-Za-z])")

    def extract(self, text: str) -> list[dict[str, Any]]:
        """Return Ollama-style tool calls if a safe deterministic parse exists."""
        normalized = self._normalize(text)
        if not normalized:
            return []

        expense_call = self._extract_expense(normalized)
        if expense_call:
            return [expense_call]

        parsed_item = self._find_item(normalized)
        amount = self._extract_amount(normalized)
        if parsed_item is None or amount is None:
            return []

        intent = self._detect_transaction_intent(normalized) or "record_sale"

        parsed_unit = self._find_unit(normalized)
        quantity, quantity_explicit = self._extract_quantity(normalized, parsed_unit, parsed_item)
        unit = parsed_unit.unit if parsed_unit else "lot"

        if quantity <= 0:
            return []

        unit_price = (
            round(amount / quantity, 2)
            if quantity_explicit and quantity > 1 and self._looks_like_total(normalized)
            else amount
        )
        arguments: dict[str, Any] = {
            "item": parsed_item.item,
            "quantity": quantity,
            "unit": unit,
            "currency": self._extract_currency(normalized),
        }

        if intent == "record_sale":
            arguments["sale_price"] = unit_price
        else:
            arguments["unit_price"] = unit_price

        return [
            {
                "function": {
                    "name": intent,
                    "arguments": arguments,
                }
            }
        ]

    def _extract_expense(self, normalized: str) -> dict[str, Any] | None:
        amount = self._extract_amount(normalized)
        if amount is None:
            return None

        category = None
        for candidate, markers in self.EXPENSE_MARKERS.items():
            if any(marker in normalized for marker in markers):
                category = candidate
                break

        if category is None:
            return None

        return {
            "function": {
                "name": "record_expense",
                "arguments": {
                    "category": category,
                    "amount": amount,
                    "description": category.replace("_", " "),
                    "currency": self._extract_currency(normalized),
                },
            }
        }

    def _detect_transaction_intent(self, normalized: str) -> str | None:
        if self._contains_marker(normalized, self.SALE_MARKERS):
            return "record_sale"
        if self._contains_marker(normalized, self.PURCHASE_MARKERS):
            return "record_purchase"
        return None

    def _find_item(self, normalized: str) -> ParsedItem | None:
        padded = f" {normalized} "
        for phrase, item in sorted(self.ITEM_PHRASES.items(), key=lambda entry: len(entry[0]), reverse=True):
            phrase_normalized = self._normalize(phrase)
            match = re.search(rf"(?<!\w){re.escape(phrase_normalized)}(?!\w)", padded)
            if match:
                return ParsedItem(item=item, start=max(match.start() - 1, 0), end=max(match.end() - 1, 0))
        return None

    def _find_unit(self, normalized: str) -> ParsedUnit | None:
        tokens = normalized.split()
        for index, token in enumerate(tokens):
            unit = UNIT_ALIASES.get(token)
            if unit:
                return ParsedUnit(unit=unit, index=index)
        return None

    def _extract_quantity(self, normalized: str, unit: ParsedUnit | None, item: ParsedItem) -> tuple[float, bool]:
        tokens = normalized.split()
        numbers = [(match.start(), float(match.group(0))) for match in self._NUMBER_RE.finditer(normalized)]

        if unit and unit.index > 0:
            previous = tokens[unit.index - 1]
            if self._is_number(previous):
                return float(previous), True

        numbers_before_item = [value for position, value in numbers if position < item.start]
        if numbers_before_item:
            return numbers_before_item[-1], True

        amount = self._extract_amount(normalized)
        non_amount_numbers = [value for _, value in numbers if amount is None or value != amount]
        if len(non_amount_numbers) == 1:
            return non_amount_numbers[0], True

        return 1.0, False

    def _extract_amount(self, normalized: str) -> float | None:
        money_patterns = [
            r"(?:ghs|cedi|cedis|naira|ngn|kes|shillings?|xof|cfa)\s+(\d+(?:\.\d+)?)",
            r"(\d+(?:\.\d+)?)\s*(?:ghs|cedi|cedis|naira|ngn|kes|shillings?|xof|cfa)",
        ]
        for pattern in money_patterns:
            match = re.search(pattern, normalized)
            if match:
                return round(float(match.group(1)), 2)

        numbers = [float(match.group(0)) for match in self._NUMBER_RE.finditer(normalized)]
        if not numbers:
            return None
        return round(numbers[-1], 2)

    def _extract_currency(self, normalized: str) -> str:
        for alias in sorted(CURRENCY_ALIASES, key=len, reverse=True):
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
                return normalize_currency_code(alias)
        return "GHS"

    @staticmethod
    def _looks_like_total(normalized: str) -> bool:
        return any(marker in normalized for marker in ("total", "altogether", "nyinaa", "jumla"))

    @classmethod
    def _contains_marker(cls, normalized: str, markers: set[str]) -> bool:
        return any(re.search(rf"(?<!\w){re.escape(cls._normalize(marker))}(?!\w)", normalized) for marker in markers)

    @classmethod
    def _normalize(cls, text: str) -> str:
        twi_keyboard_normalized = re.sub(
            r"(?<=[a-zA-Z])3|3(?=[a-zA-Z])",
            "e",
            text.replace(")", "ɔ"),
        )
        transliterated = (
            twi_keyboard_normalized.lower()
            .replace("ɔ", "o")
            .replace("ɛ", "e")
            .replace("₵", " ghs ")
            .replace("₦", " ngn ")
            .replace("₵", " ghs ")
        )
        asciiish = unicodedata.normalize("NFKD", transliterated).encode("ascii", "ignore").decode("ascii")
        return " ".join(re.sub(r"[^a-z0-9.]+", " ", asciiish).split())

    @staticmethod
    def _is_number(value: str) -> bool:
        try:
            float(value)
        except ValueError:
            return False
        return True
