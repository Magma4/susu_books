"""
Susu Books — Demo Seed Script
Populates the database with 14 days of realistic transaction data for Ama,
an Accra market trader who sells rice, onions, palm oil, tomatoes, and plantains.

Usage:
    cd backend && python seed.py
    # or from Docker: docker exec susu-backend python seed.py
"""

from __future__ import annotations

import asyncio
import logging
import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

# Add backend directory to path when executed directly.
sys.path.insert(0, str(Path(__file__).parent))

from database import AsyncSessionLocal, create_tables
from models import DailySummary, Inventory, Transaction
from services.inventory_service import InventoryService
from services.report_service import ReportService

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")

random.seed(42)

AMA_ITEMS = {
    "rice": {
        "unit": "bags",
        "buy_range": (115, 130),
        "sell_range": (165, 195),
        "daily_buy": (0, 10),
        "daily_sell": (0, 3),
        "starting_stock": 20.0,
    },
    "onions": {
        "unit": "kg",
        "buy_range": (5, 8),
        "sell_range": (11, 15),
        "daily_buy": (0, 30),
        "daily_sell": (0, 8),
        "starting_stock": 50.0,
    },
    "palm oil": {
        "unit": "liters",
        "buy_range": (32, 40),
        "sell_range": (52, 65),
        "daily_buy": (0, 20),
        "daily_sell": (0, 5),
        "starting_stock": 30.0,
    },
    "tomatoes": {
        "unit": "crates",
        "buy_range": (45, 58),
        "sell_range": (70, 90),
        "daily_buy": (0, 5),
        "daily_sell": (0, 2),
        "starting_stock": 10.0,
    },
    "plantains": {
        "unit": "bunches",
        "buy_range": (18, 25),
        "sell_range": (32, 42),
        "daily_buy": (0, 15),
        "daily_sell": (0, 5),
        "starting_stock": 25.0,
    },
}

SUPPLIERS = {
    "rice": ["Kofi", "Kofi", "Makola Wholesale"],
    "onions": ["Makola Wholesale", "Abena", "Makola Wholesale"],
    "palm oil": ["Abena", "Abena", "Makola Wholesale"],
    "tomatoes": ["Abena", "Makola Wholesale"],
    "plantains": ["Kofi", "Makola Wholesale"],
}

CUSTOMERS = ["Maame", "Akosua", "Kojo", None, None, None]

EXPENSE_CATEGORIES = {
    "transport": (10, 25, "Trotro to Makola Market"),
    "market_fee": (5, 10, "Daily market stall fee"),
    "phone": (5, 15, "Mobile money and phone credit"),
    "food": (8, 15, "Lunch at the market"),
}

LOW_STOCK_THRESHOLDS = {
    "rice": 5.0,
    "onions": 10.0,
    "palm oil": 5.0,
    "tomatoes": 2.0,
    "plantains": 5.0,
}

TARGET_ENDING_STOCK = {
    "palm oil": 3.0,
    "tomatoes": 1.0,
}

DAY_MULTIPLIER = {0: 1.0, 1: 1.1, 2: 1.5, 3: 1.2, 4: 1.4, 5: 1.8, 6: 0.6}
DISCRETE_UNITS = {"bags", "crates", "pieces", "bunches", "tubers", "baskets", "tins", "bowls", "cartons"}


def weighted_rand(low: float, high: float) -> float:
    """Return a float in [low, high] with slight random variation."""
    return round(random.uniform(low, high), 2)


def quantity_for_unit(unit: str, value: float) -> float:
    """Keep whole-number units tidy while allowing decimals for weights/liquids."""
    if unit in DISCRETE_UNITS:
        return float(max(1, round(value)))
    return round(max(0.5, value), 1)


def spread_hours(target_date: date, count: int) -> list[datetime]:
    """Spread timestamps across market hours (6am-7pm)."""
    base = datetime(target_date.year, target_date.month, target_date.day, 6, 0)
    if count <= 1:
        return [base + timedelta(hours=random.uniform(1, 8))]
    step = timedelta(hours=13 / max(count - 1, 1))
    times = [base + step * i + timedelta(minutes=random.randint(-20, 20)) for i in range(count)]
    return sorted(times)


async def seed(db: AsyncSession) -> None:
    """Reset the database and populate two demo weeks of realistic trading data."""
    log.info("Clearing existing data...")
    await db.execute(delete(Transaction))
    await db.execute(delete(Inventory))
    await db.execute(delete(DailySummary))
    await db.flush()

    today = date.today()
    start_date = today - timedelta(days=13)

    inv_state: dict[str, dict[str, float]] = {
        item: {
            "quantity": cfg["starting_stock"],
            "avg_cost": (cfg["buy_range"][0] + cfg["buy_range"][1]) / 2,
        }
        for item, cfg in AMA_ITEMS.items()
    }

    all_transactions: list[Transaction] = []
    total_tx = 0

    log.info("Seeding 14 days of data for Ama's market stall...")

    opening_date = start_date - timedelta(days=1)
    for index, (item, cfg) in enumerate(AMA_ITEMS.items()):
        opening_quantity = cfg["starting_stock"]
        opening_price = round(inv_state[item]["avg_cost"], 2)
        opening_time = datetime(
            opening_date.year,
            opening_date.month,
            opening_date.day,
            5,
            15 + index * 5,
        )
        all_transactions.append(
            Transaction(
                type="purchase",
                item=item,
                quantity=opening_quantity,
                unit=cfg["unit"],
                unit_price=opening_price,
                total_amount=round(opening_quantity * opening_price, 2),
                currency="GHS",
                counterparty="Opening stock",
                notes="Seeded opening balance for demo mode",
                source="manual",
                language="en",
                raw_input=f"Opening stock: {opening_quantity:g} {cfg['unit']} of {item}",
                confidence=1.0,
                created_at=opening_time,
                updated_at=opening_time,
            )
        )
        total_tx += 1

    for day_offset in range(14):
        current_date = start_date + timedelta(days=day_offset)
        weekday = current_date.weekday()
        multiplier = DAY_MULTIPLIER[weekday]
        is_restock_day = weekday in (0, 2, 4)
        is_last_two_days = day_offset >= 12

        day_transactions: list[Transaction] = []

        if is_restock_day or day_offset == 0:
            items_to_buy = list(AMA_ITEMS.keys())
            random.shuffle(items_to_buy)
            for item in items_to_buy:
                cfg = AMA_ITEMS[item]
                min_qty, max_qty = cfg["daily_buy"]
                if min_qty == max_qty == 0:
                    continue

                if is_last_two_days and item in TARGET_ENDING_STOCK:
                    continue

                qty = quantity_for_unit(
                    cfg["unit"],
                    random.uniform(max_qty * 0.3, max_qty) * multiplier * 0.6,
                )
                if qty < 1 and cfg["unit"] in DISCRETE_UNITS:
                    continue

                unit_price = weighted_rand(*cfg["buy_range"])
                total = round(qty * unit_price, 2)
                supplier = random.choice(SUPPLIERS[item])
                old_qty = inv_state[item]["quantity"]
                old_avg = inv_state[item]["avg_cost"]
                new_qty = old_qty + qty
                inv_state[item]["avg_cost"] = (old_qty * old_avg + qty * unit_price) / new_qty
                inv_state[item]["quantity"] = new_qty

                purchase_time = datetime(
                    current_date.year,
                    current_date.month,
                    current_date.day,
                    6,
                    random.randint(10, 50),
                )
                day_transactions.append(
                    Transaction(
                        type="purchase",
                        item=item,
                        quantity=qty,
                        unit=cfg["unit"],
                        unit_price=unit_price,
                        total_amount=total,
                        currency="GHS",
                        counterparty=supplier,
                        source="voice",
                        language="en",
                        raw_input=f"Bought {qty:g} {cfg['unit']} of {item} for {unit_price:.2f} each from {supplier}",
                        confidence=0.97,
                        created_at=purchase_time,
                        updated_at=purchase_time,
                    )
                )

        base_sale_count = int(random.randint(5, 9) * multiplier)
        sale_times = spread_hours(current_date, base_sale_count)

        for idx in range(base_sale_count):
            item = random.choices(
                list(AMA_ITEMS.keys()),
                weights=[3, 2, 2, 2, 2],
            )[0]
            cfg = AMA_ITEMS[item]
            current_stock = round(inv_state[item]["quantity"], 2)
            if current_stock <= 0:
                continue

            qty = quantity_for_unit(cfg["unit"], random.uniform(0.5, cfg["daily_sell"][1]))
            if current_stock < qty:
                if cfg["unit"] in DISCRETE_UNITS:
                    qty = float(int(current_stock))
                else:
                    qty = round(current_stock, 1)

            if qty <= 0:
                continue

            unit_price = weighted_rand(*cfg["sell_range"])
            total = round(qty * unit_price, 2)
            customer = random.choice(CUSTOMERS)
            inv_state[item]["quantity"] = round(max(0.0, current_stock - qty), 2)
            sale_time = sale_times[min(idx, len(sale_times) - 1)]

            day_transactions.append(
                Transaction(
                    type="sale",
                    item=item,
                    quantity=qty,
                    unit=cfg["unit"],
                    unit_price=unit_price,
                    total_amount=total,
                    currency="GHS",
                    counterparty=customer,
                    source="voice",
                    language="en",
                    raw_input=(
                        f"Sold {qty:g} {cfg['unit']} of {item} at {unit_price:.2f} each"
                        + (f" to {customer}" if customer else "")
                    ),
                    confidence=0.98,
                    created_at=sale_time,
                    updated_at=sale_time,
                )
            )

        expense_times = spread_hours(current_date, 2)
        transport_amt = weighted_rand(10, 22)
        day_transactions.append(
            Transaction(
                type="expense",
                item="Trotro to Makola Market",
                total_amount=transport_amt,
                currency="GHS",
                category="transport",
                source="voice",
                language="en",
                raw_input=f"Transport cost {transport_amt:.2f} cedis",
                confidence=0.99,
                created_at=expense_times[0],
                updated_at=expense_times[0],
            )
        )

        if is_restock_day:
            fee = weighted_rand(5, 10)
            fee_time = expense_times[1] if len(expense_times) > 1 else expense_times[0]
            day_transactions.append(
                Transaction(
                    type="expense",
                    item="Daily market stall fee",
                    total_amount=fee,
                    currency="GHS",
                    category="market_fee",
                    source="voice",
                    language="en",
                    raw_input=f"Market stall fee {fee:.2f} cedis",
                    confidence=0.99,
                    created_at=fee_time,
                    updated_at=fee_time,
                )
            )

        if random.random() < 0.35:
            category, (low, high, description) = random.choice(list(EXPENSE_CATEGORIES.items()))
            if category not in {"transport", "market_fee"}:
                amount = weighted_rand(low, high)
                misc_time = spread_hours(current_date, 1)[0]
                day_transactions.append(
                    Transaction(
                        type="expense",
                        item=description,
                        total_amount=amount,
                        currency="GHS",
                        category=category,
                        source="voice",
                        language="en",
                        raw_input=f"{description} cost {amount:.2f} cedis",
                        confidence=0.95,
                        created_at=misc_time,
                        updated_at=misc_time,
                    )
                )

        all_transactions.extend(day_transactions)
        total_tx += len(day_transactions)

        revenue = sum(tx.total_amount for tx in day_transactions if tx.type == "sale")
        cost = sum(tx.total_amount for tx in day_transactions if tx.type == "purchase")
        expenses = sum(tx.total_amount for tx in day_transactions if tx.type == "expense")
        profit = revenue - cost - expenses

        log.info(
            "  %s (%s) — %s tx | rev GHS %.0f cost GHS %.0f exp GHS %.0f %s GHS %.0f",
            current_date,
            ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][weekday],
            len(day_transactions),
            revenue,
            cost,
            expenses,
            "profit" if profit >= 0 else "loss",
            profit,
        )

    final_sale_time = datetime(today.year, today.month, today.day, 18, 15)
    for item, target_quantity in TARGET_ENDING_STOCK.items():
        current_quantity = round(inv_state[item]["quantity"], 2)
        if current_quantity <= target_quantity:
            continue

        cfg = AMA_ITEMS[item]
        qty_to_sell = round(current_quantity - target_quantity, 2)
        sale_price = weighted_rand(*cfg["sell_range"])
        total = round(qty_to_sell * sale_price, 2)

        all_transactions.append(
            Transaction(
                type="sale",
                item=item,
                quantity=qty_to_sell,
                unit=cfg["unit"],
                unit_price=sale_price,
                total_amount=total,
                currency="GHS",
                counterparty="Walk-in customer",
                source="voice",
                language="en",
                raw_input=f"Sold {qty_to_sell:g} {cfg['unit']} of {item} at {sale_price:.2f} each",
                confidence=0.96,
                created_at=final_sale_time,
                updated_at=final_sale_time,
            )
        )
        inv_state[item]["quantity"] = target_quantity
        total_tx += 1

    db.add_all(all_transactions)
    await db.flush()

    log.info("Rebuilding inventory and generating cached summaries...")
    inventory_service = InventoryService(db)
    await inventory_service.rebuild_from_transactions()
    for item, threshold in LOW_STOCK_THRESHOLDS.items():
        await inventory_service.update_threshold(item, threshold)

    report_service = ReportService(db)
    for offset in range(14):
        await report_service.daily_summary(start_date + timedelta(days=offset))

    low_stock_items = await inventory_service.get_low_stock_items()
    low_stock_summary = ", ".join(
        f"{item.item} ({item.quantity:.2f} {item.unit})" for item in low_stock_items
    ) or "none"

    log.info("")
    log.info("✅ Seeded %s transactions across 14 days.", total_tx)
    log.info("   Low stock items: %s", low_stock_summary)


async def main() -> None:
    """Create tables, seed the database, and exit cleanly."""
    await create_tables()
    async with AsyncSessionLocal() as session:
        async with session.begin():
            await seed(session)

    log.info("Database ready. Start the app and the dashboard will be pre-populated!")


if __name__ == "__main__":
    asyncio.run(main())
