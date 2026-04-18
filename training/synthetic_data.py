"""
Synthetic multilingual extraction dataset generator for Susu Books.

This script creates balanced train/validation datasets for Unsloth LoRA
fine-tuning. The data mirrors the live backend contract exactly:

- same system prompt
- same eight tool names
- same argument schema conventions
- multilingual, code-switched market-style phrasing
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from ai_contract import EXTRACTION_SYSTEM_PROMPT


LANGUAGES = ("en", "tw", "ha", "pcm", "sw")
DISCRETE_UNITS = {"bags", "crates", "pieces", "bunches", "tubers", "baskets", "tins", "bowls", "cartons"}
TODAY = date.today()

INTENT_WEIGHTS: dict[str, float] = {
    "purchase": 0.23,
    "sale": 0.23,
    "expense": 0.16,
    "inventory_item": 0.12,
    "inventory_all": 0.05,
    "daily_summary": 0.08,
    "weekly_report": 0.05,
    "credit_profile": 0.04,
    "clarify": 0.04,
}

NUMBER_WORDS: dict[str, dict[int, str]] = {
    "en": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten", 12: "twelve"},
    "tw": {1: "baako", 2: "mmienu", 3: "mmiensa", 4: "anan", 5: "enum", 6: "nsia", 7: "nson", 8: "nwotwe", 9: "nkron", 10: "du"},
    "ha": {1: "daya", 2: "biyu", 3: "uku", 4: "hudu", 5: "biyar", 6: "shida", 7: "bakwai", 8: "takwas", 9: "tara", 10: "goma"},
    "sw": {1: "moja", 2: "mbili", 3: "tatu", 4: "nne", 5: "tano", 6: "sita", 7: "saba", 8: "nane", 9: "tisa", 10: "kumi"},
}

ITEMS: dict[str, dict[str, Any]] = {
    "rice": {
        "units": ["bags", "kg"],
        "price": {"bags": 120.0, "kg": 8.0},
        "currencies": ["GHS", "NGN", "KES"],
        "local_names": {
            "en": ["rice"],
            "tw": ["shinkafa", "rice"],
            "ha": ["shinkafa", "rice"],
            "pcm": ["rice", "rais"],
            "sw": ["mchele", "rice"],
        },
    },
    "onions": {
        "units": ["kg", "bags"],
        "price": {"kg": 7.0, "bags": 95.0},
        "currencies": ["GHS", "NGN"],
        "local_names": {
            "en": ["onions", "onion"],
            "tw": ["gyeene", "onions"],
            "ha": ["albasa", "onions"],
            "pcm": ["onions", "onion"],
            "sw": ["vitunguu", "onions"],
        },
    },
    "palm oil": {
        "units": ["liters", "tins"],
        "price": {"liters": 35.0, "tins": 110.0},
        "currencies": ["GHS", "NGN", "XOF"],
        "local_names": {
            "en": ["palm oil"],
            "tw": ["nkwan", "palm oil", "nkuto"],
            "ha": ["mai ja", "palm oil"],
            "pcm": ["palm oil", "red oil"],
            "sw": ["mafuta ya mawese", "palm oil"],
        },
    },
    "tomatoes": {
        "units": ["crates", "kg"],
        "price": {"crates": 55.0, "kg": 9.0},
        "currencies": ["GHS", "NGN"],
        "local_names": {
            "en": ["tomatoes", "tomato"],
            "tw": ["tomatoes", "ntomato"],
            "ha": ["tumatur", "tomato"],
            "pcm": ["tomatoes", "tomato"],
            "sw": ["nyanya", "tomatoes"],
        },
    },
    "plantain": {
        "units": ["bunches", "pieces"],
        "price": {"bunches": 24.0, "pieces": 4.0},
        "currencies": ["GHS", "XOF"],
        "local_names": {
            "en": ["plantain"],
            "tw": ["borodee", "plantain"],
            "ha": ["plantain", "ayaba"],
            "pcm": ["plantain"],
            "sw": ["ndizi", "plantain"],
        },
    },
    "beans": {
        "units": ["bags", "kg"],
        "price": {"bags": 135.0, "kg": 10.0},
        "currencies": ["GHS", "NGN", "KES"],
        "local_names": {
            "en": ["beans"],
            "tw": ["awe", "beans"],
            "ha": ["wake", "beans"],
            "pcm": ["beans"],
            "sw": ["maharagwe", "beans"],
        },
    },
    "fish": {
        "units": ["kg", "pieces"],
        "price": {"kg": 22.0, "pieces": 9.0},
        "currencies": ["GHS", "NGN", "KES"],
        "local_names": {
            "en": ["fish"],
            "tw": ["nam", "fish"],
            "ha": ["kifi", "fish"],
            "pcm": ["fish"],
            "sw": ["samaki", "fish"],
        },
    },
    "cassava": {
        "units": ["kg", "baskets"],
        "price": {"kg": 5.0, "baskets": 42.0},
        "currencies": ["GHS", "NGN", "KES"],
        "local_names": {
            "en": ["cassava"],
            "tw": ["bankye", "cassava"],
            "ha": ["rogo", "cassava"],
            "pcm": ["cassava"],
            "sw": ["mihogo", "cassava"],
        },
    },
    "groundnuts": {
        "units": ["kg", "bags"],
        "price": {"kg": 14.0, "bags": 150.0},
        "currencies": ["GHS", "NGN", "XOF"],
        "local_names": {
            "en": ["groundnuts"],
            "tw": ["nkatee", "groundnuts"],
            "ha": ["gyada", "groundnuts"],
            "pcm": ["groundnut", "groundnuts"],
            "sw": ["karanga", "groundnuts"],
        },
    },
    "pepper": {
        "units": ["kg", "crates"],
        "price": {"kg": 12.0, "crates": 65.0},
        "currencies": ["GHS", "NGN"],
        "local_names": {
            "en": ["pepper"],
            "tw": ["mako", "pepper"],
            "ha": ["barkono", "pepper"],
            "pcm": ["pepper"],
            "sw": ["pilipili", "pepper"],
        },
    },
}

EXPENSES: dict[str, list[str]] = {
    "transport": ["transport", "transport to market", "bus fare", "trotro fare", "okada fare", "boda boda fare"],
    "rent": ["shop rent", "stall rent", "space rent"],
    "utilities": ["electricity bill", "generator fuel", "water bill"],
    "food": ["lunch", "food for the stall", "breakfast at market"],
    "phone": ["phone credit", "mobile money charges", "data bundle"],
    "supplies": ["packaging materials", "nylon bags", "rubber bands"],
    "staff": ["helper wages", "porter fee", "loading fee"],
    "market_fee": ["market stall fee", "market levy", "daily market dues"],
    "other": ["table repair", "scale repair", "cleaning supplies"],
}

SUPPLIERS = {
    "gh": ["Kofi", "Abena", "Kwame", "Akosua", "Makola Wholesale"],
    "ng": ["Mama Joy", "Emeka", "Ngozi", "Musa", "Amina"],
    "ke": ["Wanjiku", "Akinyi", "Kamau", "Hassan", "Mama Mboga"],
}

CUSTOMERS = {
    "gh": ["Maame", "Nana", "Sister Ama", "Kojo"],
    "ng": ["Iya Sade", "Mama Ngozi", "Auntie Chioma", "Uche"],
    "ke": ["Mama Wanjiku", "Bibi Asha", "Omondi", "Akinyi"],
}

CLARIFY_SAMPLES = {
    "en": ["eh the thing I said before", "hmm write that one there somehow", "123 sss market hmm", "I no finish talk but do am"],
    "tw": ["hmm na mekae no ara", "kakra bi na mede", "agya hmm 3 9 no", "yaa na no no"],
    "ha": ["eh wannan abu can dai", "ka rubuta wancan kawai", "mmm 7 9 kasuwa", "na manta abin"],
    "pcm": ["abeg that thing wey I talk", "hmm just put am somehow", "market market 7 3 eh", "no be clear abeg"],
    "sw": ["ile kitu nilisema tu", "andika ile ya jana basi", "mmm sokoni 8 4", "sikueleza vizuri"],
}


@dataclass(frozen=True)
class SyntheticExample:
    messages: list[dict[str, Any]]
    meta: dict[str, Any]

    def to_raw_record(self) -> dict[str, Any]:
        return {"messages": self.messages, "_meta": self.meta}


def maybe_number_word(value: float, language: str, rng: random.Random) -> str:
    if value.is_integer():
        integer_value = int(value)
        if integer_value in NUMBER_WORDS.get(language, {}) and rng.random() < 0.25:
            return NUMBER_WORDS[language][integer_value]
    return f"{value:g}"


def currency_spoken(currency: str, language: str, rng: random.Random) -> str:
    spoken = {
        "GHS": {
            "en": ["cedis", "GHS", "Ghana cedis"],
            "tw": ["cedis", "sika", "GHS"],
            "ha": ["cedis", "GHS"],
            "pcm": ["cedis", "Ghana cedis"],
            "sw": ["cedis", "GHS"],
        },
        "NGN": {
            "en": ["naira", "NGN"],
            "tw": ["naira"],
            "ha": ["naira", "NGN"],
            "pcm": ["naira", "NGN"],
            "sw": ["naira"],
        },
        "KES": {
            "en": ["shillings", "KES"],
            "tw": ["shillings"],
            "ha": ["shillings"],
            "pcm": ["shillings"],
            "sw": ["shilingi", "KES"],
        },
        "XOF": {
            "en": ["CFA", "CFA francs", "XOF"],
            "tw": ["CFA"],
            "ha": ["CFA"],
            "pcm": ["CFA"],
            "sw": ["CFA", "faranga za CFA"],
        },
    }
    return rng.choice(spoken.get(currency, {}).get(language, [currency]))


def choose_region(currency: str, language: str, rng: random.Random) -> str:
    if currency == "KES" or language == "sw":
        return "ke"
    if currency == "NGN" or language in {"ha", "pcm"}:
        return rng.choice(["ng", "gh"])
    return "gh"


def choose_local_item_name(item: str, language: str, rng: random.Random) -> str:
    variants = ITEMS[item]["local_names"].get(language, [item])
    return rng.choice(variants)


def sample_unit(item: str, rng: random.Random) -> str:
    return rng.choice(ITEMS[item]["units"])


def sample_currency(item: str, language: str, rng: random.Random) -> str:
    options = list(ITEMS[item]["currencies"])
    if language == "sw" and "KES" in options and rng.random() < 0.7:
        return "KES"
    if language == "ha" and "NGN" in options and rng.random() < 0.6:
        return "NGN"
    if language == "pcm" and "NGN" in options and rng.random() < 0.55:
        return "NGN"
    if language == "tw" and "GHS" in options and rng.random() < 0.75:
        return "GHS"
    return rng.choice(options)


def currency_multiplier(currency: str) -> float:
    return {
        "GHS": 1.0,
        "NGN": 8.5,
        "KES": 11.0,
        "XOF": 9.0,
    }.get(currency, 1.0)


def sample_quantity(unit: str, rng: random.Random) -> float:
    if unit in DISCRETE_UNITS:
        return float(rng.choice([1, 2, 3, 4, 5, 6, 8, 10, 12, 15]))
    return float(rng.choice([0.5, 1, 1.5, 2, 2.5, 3, 5, 7.5, 10, 12.5]))


def sample_price(item: str, unit: str, currency: str, rng: random.Random) -> float:
    base = float(ITEMS[item]["price"][unit])
    noisy = base * rng.uniform(0.88, 1.18) * currency_multiplier(currency)
    if noisy >= 100:
        return round(noisy / 5) * 5
    if noisy >= 20:
        return round(noisy / 2) * 2
    return round(noisy, 2)


def render_purchase_utterance(
    language: str,
    item_name: str,
    quantity: float,
    unit: str,
    unit_price: float,
    total_amount: float,
    supplier: str | None,
    currency: str,
    rng: random.Random,
) -> str:
    quantity_text = maybe_number_word(quantity, language, rng)
    money = currency_spoken(currency, language, rng)
    supplier_text = {
        "en": f" from {supplier}" if supplier else "",
        "tw": f" wo {supplier} ho" if supplier else "",
        "ha": f" daga {supplier}" if supplier else "",
        "pcm": f" from {supplier}" if supplier else "",
        "sw": f" kutoka kwa {supplier}" if supplier else "",
    }[language]
    mode = rng.choice(["unit_price", "total_only", "both"])

    if language == "en":
        options = [
            f"I bought {quantity_text} {unit} of {item_name}{supplier_text} for {unit_price:g} {money} each",
            f"Restocked {item_name}: {quantity_text} {unit}{supplier_text} at {unit_price:g} {money} per unit",
            f"I paid {total_amount:g} {money} for {quantity_text} {unit} of {item_name}{supplier_text}",
            f"Bought {quantity_text} {unit} {item_name}{supplier_text}, total {total_amount:g} {money}, {unit_price:g} each",
        ]
    elif language == "tw":
        options = [
            f"Metoo {item_name} {quantity_text} {unit} a {unit_price:g} {money} koro koro{supplier_text}",
            f"Mede {total_amount:g} {money} too {item_name} {quantity_text} {unit}{supplier_text}",
            f"Yeto {item_name} {quantity_text} {unit}{supplier_text}, {unit_price:g} {money} biara",
            f"Metoo {item_name}{supplier_text} - {quantity_text} {unit}, ne nyinaa {total_amount:g} {money}",
        ]
    elif language == "ha":
        options = [
            f"Na saya {item_name} {quantity_text} {unit}{supplier_text} da {unit_price:g} {money} kowanne",
            f"Na biya {total_amount:g} {money} don {item_name} {quantity_text} {unit}{supplier_text}",
            f"Na sayo {item_name}{supplier_text} - {quantity_text} {unit}, {unit_price:g} {money} kowane",
            f"Na kara stock na {item_name} {quantity_text} {unit}{supplier_text}, jimla {total_amount:g} {money}",
        ]
    elif language == "pcm":
        options = [
            f"I buy {item_name} {quantity_text} {unit}{supplier_text} for {unit_price:g} {money} each",
            f"Na pay {total_amount:g} {money} for {quantity_text} {unit} {item_name}{supplier_text}",
            f"I don restock {item_name} {quantity_text} {unit}{supplier_text}, {unit_price:g} {money} each one",
            f"Buy {item_name}{supplier_text}: {quantity_text} {unit}, total {total_amount:g} {money}",
        ]
    else:
        options = [
            f"Nimenunua {item_name} {quantity_text} {unit}{supplier_text} kwa {unit_price:g} {money} kila moja",
            f"Nimelipa {total_amount:g} {money} kwa {quantity_text} {unit} za {item_name}{supplier_text}",
            f"Nimeongeza stock ya {item_name}: {quantity_text} {unit}{supplier_text}, {unit_price:g} {money} kila moja",
            f"Nunua {item_name}{supplier_text} - {quantity_text} {unit}, jumla {total_amount:g} {money}",
        ]

    if mode == "unit_price":
        return rng.choice(options[:2])
    if mode == "total_only":
        return rng.choice(options[2:3] or options)
    return rng.choice(options)


def render_sale_utterance(
    language: str,
    item_name: str,
    quantity: float,
    unit: str,
    sale_price: float,
    total_amount: float,
    customer: str | None,
    currency: str,
    rng: random.Random,
) -> str:
    quantity_text = maybe_number_word(quantity, language, rng)
    money = currency_spoken(currency, language, rng)
    customer_text = {
        "en": f" to {customer}" if customer else "",
        "tw": f" maa {customer}" if customer else "",
        "ha": f" wa {customer}" if customer else "",
        "pcm": f" give {customer}" if customer else "",
        "sw": f" kwa {customer}" if customer else "",
    }[language]
    mode = rng.choice(["unit_price", "total_only", "both"])

    if language == "en":
        options = [
            f"I sold {quantity_text} {unit} of {item_name}{customer_text} for {sale_price:g} {money} each",
            f"Sold {quantity_text} {unit} {item_name}{customer_text}, {sale_price:g} {money} per unit",
            f"I received {total_amount:g} {money} from selling {quantity_text} {unit} of {item_name}{customer_text}",
            f"Sale: {item_name}, {quantity_text} {unit}{customer_text}, total {total_amount:g} {money}",
        ]
    elif language == "tw":
        options = [
            f"Meton {item_name} {quantity_text} {unit}{customer_text} a {sale_price:g} {money} biara",
            f"Yeton {item_name} {quantity_text} {unit}{customer_text}, {sale_price:g} {money} koro koro",
            f"Megyee {total_amount:g} {money} fii {item_name} {quantity_text} {unit} a meton no mu",
            f"Tontoo no ye {item_name} {quantity_text} {unit}, ne nyinaa {total_amount:g} {money}",
        ]
    elif language == "ha":
        options = [
            f"Na sayar da {item_name} {quantity_text} {unit}{customer_text} a {sale_price:g} {money} kowanne",
            f"An sayar da {item_name} {quantity_text} {unit}{customer_text}, {sale_price:g} {money} kowane",
            f"Na samu {total_amount:g} {money} daga sayar da {item_name} {quantity_text} {unit}{customer_text}",
            f"Tallace-tallace: {item_name} {quantity_text} {unit}, jimla {total_amount:g} {money}",
        ]
    elif language == "pcm":
        options = [
            f"I sell {item_name} {quantity_text} {unit}{customer_text} for {sale_price:g} {money} each",
            f"Na sell {quantity_text} {unit} {item_name}{customer_text}, {sale_price:g} {money} each one",
            f"I get {total_amount:g} {money} from {quantity_text} {unit} {item_name}{customer_text}",
            f"Sale don happen: {item_name}, {quantity_text} {unit}, total {total_amount:g} {money}",
        ]
    else:
        options = [
            f"Nimeuza {item_name} {quantity_text} {unit}{customer_text} kwa {sale_price:g} {money} kila moja",
            f"Uuzaji wa {item_name}: {quantity_text} {unit}{customer_text}, {sale_price:g} {money} kila moja",
            f"Nimepata {total_amount:g} {money} kwa kuuza {quantity_text} {unit} za {item_name}{customer_text}",
            f"Sell ya {item_name} {quantity_text} {unit}, jumla {total_amount:g} {money}",
        ]

    if mode == "unit_price":
        return rng.choice(options[:2])
    if mode == "total_only":
        return rng.choice(options[2:3] or options)
    return rng.choice(options)


def render_expense_utterance(
    language: str,
    description: str,
    amount: float,
    category: str,
    currency: str,
    rng: random.Random,
) -> str:
    money = currency_spoken(currency, language, rng)
    if language == "en":
        templates = [
            f"{description} cost {amount:g} {money}",
            f"I spent {amount:g} {money} on {description}",
            f"{category.replace('_', ' ')} today was {amount:g} {money}",
        ]
    elif language == "tw":
        templates = [
            f"{description} ye {amount:g} {money}",
            f"Mede {amount:g} {money} mae {description}",
            f"{category.replace('_', ' ')} no cost {amount:g} {money}",
        ]
    elif language == "ha":
        templates = [
            f"{description} ya ci {amount:g} {money}",
            f"Na kashe {amount:g} {money} kan {description}",
            f"Kudin {category.replace('_', ' ')} yau {amount:g} {money}",
        ]
    elif language == "pcm":
        templates = [
            f"{description} cost me {amount:g} {money}",
            f"I spend {amount:g} {money} for {description}",
            f"{category.replace('_', ' ')} money na {amount:g} {money}",
        ]
    else:
        templates = [
            f"{description} imenigharimu {amount:g} {money}",
            f"Nimetumia {amount:g} {money} kwa {description}",
            f"Gharama ya {category.replace('_', ' ')} leo ni {amount:g} {money}",
        ]
    return rng.choice(templates)


def render_inventory_item_query(language: str, item_name: str, rng: random.Random) -> str:
    templates = {
        "en": [f"How much {item_name} do I have left?", f"Check my {item_name} stock", f"What is my {item_name} balance?"],
        "tw": [f"{item_name} no aka sen?", f"Hwɛ me {item_name} stock", f"{item_name} a aka no yɛ sen?"],
        "ha": [f"Nawa {item_name} ya rage mini?", f"Duba min {item_name} nake da shi", f"Akwai {item_name} nawa a stock?"],
        "pcm": [f"How much {item_name} I get?", f"Check my {item_name} stock", f"{item_name} remain how many?"],
        "sw": [f"Nimebakiwa na {item_name} kiasi gani?", f"Angalia stock ya {item_name}", f"{item_name} imebaki kiasi gani?"],
    }
    return rng.choice(templates[language])


def render_inventory_all_query(language: str, rng: random.Random) -> str:
    templates = {
        "en": ["What do I have in stock?", "Show all my inventory", "List my stock levels"],
        "tw": ["Dɛn na ɛwɔ me stock mu?", "Kyere me me nneɛma a ɛwɔ stock mu", "Me stock nyinaa no ɛte sɛn?"],
        "ha": ["Me nake da a stock?", "Nuna mini duk kayana", "Me ke cikin stock duka?"],
        "pcm": ["Wetin dey my stock?", "Show all my inventory", "Make I see everything wey remain"],
        "sw": ["Nina nini kwenye stock?", "Nionyeshe inventory yote", "Bidhaa zangu zote zimebakia kiasi gani?"],
    }
    return rng.choice(templates[language])


def render_daily_query(language: str, target_date: str | None, rng: random.Random) -> str:
    if target_date:
        templates = {
            "en": [f"How did I do on {target_date}?", f"Show me summary for {target_date}"],
            "tw": [f"Na {target_date} deɛ, medeɛn na meyɛe?", f"Fa {target_date} summary no ma me"],
            "ha": [f"Yaya nayi a ranar {target_date}?", f"Nuna mini summary na {target_date}"],
            "pcm": [f"How I do for {target_date}?", f"Show me summary for {target_date}"],
            "sw": [f"Nilifanyaje tarehe {target_date}?", f"Nionyeshe muhtasari wa {target_date}"],
        }
        return rng.choice(templates[language])

    templates = {
        "en": ["How did I do today?", "Give me today's summary", "How be today's business?"],
        "tw": ["Ɛnnɛ meyɛe sɛn?", "Ma me ɛnnɛ summary", "Ɛnnɛ aguadi no ɛte sɛn?"],
        "ha": ["Yaya kasuwanci yau?", "Ba ni summary na yau", "Na yi yaya yau?"],
        "pcm": ["How today go?", "Give me today summary", "Business today how e be?"],
        "sw": ["Leo biashara imekuwaje?", "Nipe muhtasari wa leo", "Nimefanyaje leo?"],
    }
    return rng.choice(templates[language])


def render_weekly_query(language: str, rng: random.Random) -> str:
    templates = {
        "en": ["How did I do this week?", "Show my weekly report", "What happened over the last 7 days?"],
        "tw": ["Nnawɔtwe yi meyɛe sɛn?", "Ma me weekly report", "Nnanson a atwam no summary no bɛyɛ dɛn?"],
        "ha": ["Yaya wannan makon ya kasance?", "Nuna min weekly report", "Me ya faru cikin kwanaki bakwai?"],
        "pcm": ["This week how e be?", "Show my weekly report", "How market waka go this week?"],
        "sw": ["Wiki hii imekuwaje?", "Nionyeshe weekly report", "Siku saba zilizopita zimekuwaje?"],
    }
    return rng.choice(templates[language])


def render_credit_query(language: str, days: int | None, rng: random.Random) -> str:
    days_text = f" for the last {days} days" if days else ""
    templates = {
        "en": [f"Export my credit profile{days_text}", f"Prepare lender summary{days_text}", f"I need a loan report{days_text}"],
        "tw": [f"Fa me credit profile no ma me{days_text}", f"Yɛ me lender summary{days_text}", f"Mepɛ loan report{days_text}"],
        "ha": [f"Fitar min da credit profile{days_text}", f"Yi min lender summary{days_text}", f"Ina bukatar loan report{days_text}"],
        "pcm": [f"Export my credit profile{days_text}", f"Make lender summary for me{days_text}", f"I need loan report{days_text}"],
        "sw": [f"Nipe credit profile{days_text}", f"Niandalie lender summary{days_text}", f"Nahitaji loan report{days_text}"],
    }
    return rng.choice(templates[language])


def make_messages(user_text: str, function_name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "type": "function",
                    "function": {"name": function_name, "arguments": arguments},
                }
            ],
        },
    ]


def make_purchase_example(language: str, rng: random.Random) -> SyntheticExample:
    item = rng.choice(list(ITEMS.keys()))
    unit = sample_unit(item, rng)
    quantity = sample_quantity(unit, rng)
    currency = sample_currency(item, language, rng)
    unit_price = sample_price(item, unit, currency, rng)
    total_amount = round(quantity * unit_price, 2)
    region = choose_region(currency, language, rng)
    supplier = rng.choice(SUPPLIERS[region]) if rng.random() < 0.65 else None
    user_text = render_purchase_utterance(
        language=language,
        item_name=choose_local_item_name(item, language, rng),
        quantity=quantity,
        unit=unit,
        unit_price=unit_price,
        total_amount=total_amount,
        supplier=supplier,
        currency=currency,
        rng=rng,
    )
    arguments: dict[str, Any] = {
        "item": item,
        "quantity": quantity,
        "unit_price": unit_price,
        "unit": unit,
        "currency": currency,
    }
    if supplier:
        arguments["supplier"] = supplier
    return SyntheticExample(
        messages=make_messages(user_text, "record_purchase", arguments),
        meta={"language": language, "intent": "purchase", "function_name": "record_purchase", "item": item},
    )


def make_sale_example(language: str, rng: random.Random) -> SyntheticExample:
    item = rng.choice(list(ITEMS.keys()))
    unit = sample_unit(item, rng)
    quantity = sample_quantity(unit, rng)
    currency = sample_currency(item, language, rng)
    sale_price = round(sample_price(item, unit, currency, rng) * rng.uniform(1.12, 1.45), 2)
    total_amount = round(quantity * sale_price, 2)
    region = choose_region(currency, language, rng)
    customer = rng.choice(CUSTOMERS[region]) if rng.random() < 0.55 else None
    user_text = render_sale_utterance(
        language=language,
        item_name=choose_local_item_name(item, language, rng),
        quantity=quantity,
        unit=unit,
        sale_price=sale_price,
        total_amount=total_amount,
        customer=customer,
        currency=currency,
        rng=rng,
    )
    arguments: dict[str, Any] = {
        "item": item,
        "quantity": quantity,
        "sale_price": sale_price,
        "unit": unit,
        "currency": currency,
    }
    if customer:
        arguments["customer"] = customer
    return SyntheticExample(
        messages=make_messages(user_text, "record_sale", arguments),
        meta={"language": language, "intent": "sale", "function_name": "record_sale", "item": item},
    )


def sample_expense_currency(language: str, rng: random.Random) -> str:
    if language == "sw":
        return "KES"
    if language == "ha":
        return rng.choice(["NGN", "GHS"])
    if language == "pcm":
        return rng.choice(["NGN", "GHS"])
    return rng.choice(["GHS", "NGN", "KES", "XOF"])


def make_expense_example(language: str, rng: random.Random) -> SyntheticExample:
    category = rng.choice(list(EXPENSES.keys()))
    description = rng.choice(EXPENSES[category])
    currency = sample_expense_currency(language, rng)
    amount = float(rng.choice([5, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150, 200, 250]))
    user_text = render_expense_utterance(language, description, amount, category, currency, rng)
    return SyntheticExample(
        messages=make_messages(
            user_text,
            "record_expense",
            {"category": category, "amount": amount, "description": description, "currency": currency},
        ),
        meta={"language": language, "intent": "expense", "function_name": "record_expense", "category": category},
    )


def make_inventory_item_example(language: str, rng: random.Random) -> SyntheticExample:
    item = rng.choice(list(ITEMS.keys()))
    user_text = render_inventory_item_query(language, choose_local_item_name(item, language, rng), rng)
    return SyntheticExample(
        messages=make_messages(user_text, "check_inventory", {"item": item}),
        meta={"language": language, "intent": "inventory_item", "function_name": "check_inventory", "item": item},
    )


def make_inventory_all_example(language: str, rng: random.Random) -> SyntheticExample:
    return SyntheticExample(
        messages=make_messages(render_inventory_all_query(language, rng), "check_inventory", {}),
        meta={"language": language, "intent": "inventory_all", "function_name": "check_inventory"},
    )


def make_daily_summary_example(language: str, rng: random.Random) -> SyntheticExample:
    include_date = rng.random() < 0.35
    target_date = (TODAY - timedelta(days=rng.randint(1, 21))).isoformat() if include_date else None
    arguments = {"date": target_date} if target_date else {}
    return SyntheticExample(
        messages=make_messages(render_daily_query(language, target_date, rng), "daily_summary", arguments),
        meta={"language": language, "intent": "daily_summary", "function_name": "daily_summary"},
    )


def make_weekly_report_example(language: str, rng: random.Random) -> SyntheticExample:
    return SyntheticExample(
        messages=make_messages(render_weekly_query(language, rng), "weekly_report", {}),
        meta={"language": language, "intent": "weekly_report", "function_name": "weekly_report"},
    )


def make_credit_profile_example(language: str, rng: random.Random) -> SyntheticExample:
    days = rng.choice([None, 90, 120, 180, 365])
    arguments = {"days": days} if days is not None else {}
    return SyntheticExample(
        messages=make_messages(render_credit_query(language, days, rng), "export_credit_profile", arguments),
        meta={"language": language, "intent": "credit_profile", "function_name": "export_credit_profile"},
    )


def make_clarify_example(language: str, rng: random.Random) -> SyntheticExample:
    return SyntheticExample(
        messages=make_messages(rng.choice(CLARIFY_SAMPLES[language]), "clarify_input", {"reason": "unclear_input"}),
        meta={"language": language, "intent": "clarify", "function_name": "clarify_input"},
    )


EXAMPLE_BUILDERS: dict[str, Callable[[str, random.Random], SyntheticExample]] = {
    "purchase": make_purchase_example,
    "sale": make_sale_example,
    "expense": make_expense_example,
    "inventory_item": make_inventory_item_example,
    "inventory_all": make_inventory_all_example,
    "daily_summary": make_daily_summary_example,
    "weekly_report": make_weekly_report_example,
    "credit_profile": make_credit_profile_example,
    "clarify": make_clarify_example,
}


def distribute_counts(total: int, weights: dict[str, float]) -> dict[str, int]:
    raw = {key: total * value for key, value in weights.items()}
    counts = {key: int(value) for key, value in raw.items()}
    assigned = sum(counts.values())
    leftovers = sorted(
        ((key, raw[key] - counts[key]) for key in weights),
        key=lambda item: item[1],
        reverse=True,
    )
    for key, _ in leftovers[: total - assigned]:
        counts[key] += 1
    return counts


def build_split(total_examples: int, seed: int, split_name: str) -> list[SyntheticExample]:
    rng = random.Random(seed)
    per_language = distribute_counts(total_examples, {language: 1 / len(LANGUAGES) for language in LANGUAGES})
    examples: list[SyntheticExample] = []
    for language in LANGUAGES:
        intent_counts = distribute_counts(per_language[language], INTENT_WEIGHTS)
        for intent, count in intent_counts.items():
            builder = EXAMPLE_BUILDERS[intent]
            for _ in range(count):
                example = builder(language, rng)
                examples.append(
                    SyntheticExample(
                        messages=example.messages,
                        meta={**example.meta, "split": split_name},
                    )
                )
    rng.shuffle(examples)
    return examples


def format_tool_calls_for_sft(tool_calls: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for tool_call in tool_calls:
        function_payload = {
            "name": tool_call["function"]["name"],
            "arguments": tool_call["function"]["arguments"],
        }
        blocks.append(f"<tool_call>\n{json.dumps(function_payload, ensure_ascii=False, sort_keys=True)}\n</tool_call>")
    return "\n".join(blocks)


def format_for_sft(example: SyntheticExample) -> dict[str, Any]:
    system_message = example.messages[0]["content"]
    user_message = example.messages[1]["content"]
    tool_calls = example.messages[2]["tool_calls"]
    text = (
        f"<start_of_turn>user\n{system_message}\n\n{user_message}<end_of_turn>\n"
        f"<start_of_turn>model\n{format_tool_calls_for_sft(tool_calls)}<end_of_turn>"
    )
    return {"text": text, "_meta": example.meta}


def save_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_manifest(train_examples: list[SyntheticExample], val_examples: list[SyntheticExample], seed: int) -> dict[str, Any]:
    def summarize(examples: list[SyntheticExample]) -> dict[str, dict[str, int]]:
        by_language = Counter(example.meta["language"] for example in examples)
        by_intent = Counter(example.meta["intent"] for example in examples)
        by_function = Counter(example.meta["function_name"] for example in examples)
        return {
            "by_language": dict(sorted(by_language.items())),
            "by_intent": dict(sorted(by_intent.items())),
            "by_function": dict(sorted(by_function.items())),
        }

    return {
        "seed": seed,
        "system_prompt_word_count": len(EXTRACTION_SYSTEM_PROMPT.split()),
        "train_examples": len(train_examples),
        "validation_examples": len(val_examples),
        "intents": list(INTENT_WEIGHTS.keys()),
        "languages": list(LANGUAGES),
        "train_distribution": summarize(train_examples),
        "validation_distribution": summarize(val_examples),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic multilingual Susu Books training data.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "training" / "data")
    parser.add_argument("--train-examples", type=int, default=2700)
    parser.add_argument("--val-examples", type=int, default=300)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.train_examples <= 0 or args.val_examples <= 0:
        raise SystemExit("train-examples and val-examples must both be positive.")

    train_examples = build_split(args.train_examples, args.seed, "train")
    val_examples = build_split(args.val_examples, args.seed + 1, "validation")

    train_raw = [example.to_raw_record() for example in train_examples]
    val_raw = [example.to_raw_record() for example in val_examples]
    train_sft = [format_for_sft(example) for example in train_examples]
    val_sft = [format_for_sft(example) for example in val_examples]

    output_dir: Path = args.output_dir
    save_jsonl(output_dir / "synthetic_train_raw.jsonl", train_raw)
    save_jsonl(output_dir / "synthetic_val_raw.jsonl", val_raw)
    save_jsonl(output_dir / "synthetic_train_sft.jsonl", train_sft)
    save_jsonl(output_dir / "synthetic_val_sft.jsonl", val_sft)

    manifest = build_manifest(train_examples, val_examples, args.seed)
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    preview_rows = train_raw[:5] + val_raw[:5]
    (output_dir / "preview.json").write_text(json.dumps(preview_rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print("Synthetic dataset generated.")
    print(f"  Train examples : {len(train_examples)}")
    print(f"  Val examples   : {len(val_examples)}")
    print(f"  Output dir     : {output_dir}")
    print("  Train intents  :", dict(sorted(Counter(example.meta["intent"] for example in train_examples).items())))
    print("  Train languages:", dict(sorted(Counter(example.meta["language"] for example in train_examples).items())))


if __name__ == "__main__":
    main()
