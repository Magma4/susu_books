"""
Susu Books — Demo Seed Script
Populates the database with 14 days of realistic transaction data for Ama,
a market woman in Accra who sells rice, onions, palm oil, tomatoes, and plantains.

Usage:
    cd backend && python seed.py
    # or from Docker:  docker exec susu-backend python seed.py
"""

import asyncio
import logging
import random
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import select, delete

from config import get_settings
from database import Base
from models import Transaction, Inventory, DailySummary

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("seed")

settings = get_settings()

# ---------------------------------------------------------------------------
# Configuration — Ama's stall
# ---------------------------------------------------------------------------

random.seed(42)  # reproducible demo data

AMA_ITEMS = {
    "rice": {
        "unit": "bags",
        "buy_range": (115, 130),
        "sell_range": (165, 195),
        "daily_buy": (0, 10),    # purchase qty range per order
        "daily_sell": (0, 3),    # sales qty range per transaction
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
    "palm_oil": {
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
    "rice": ["Kofi", "Kofi", "Market Wholesale"],
    "onions": ["Market Wholesale", "Abena", "Market Wholesale"],
    "palm_oil": ["Abena", "Abena", "Market Wholesale"],
    "tomatoes": ["Abena", "Market Wholesale"],
    "plantains": ["Kofi", "Market Wholesale"],
}

CUSTOMERS = ["Maame", "Akosua", None, None, None, None]  # mostly anonymous

EXPENSE_CATEGORIES = {
    "transport": (10, 25, "Trotro to Makola Market"),
    "market_fee": (5, 10, "Daily market stall fee"),
    "phone": (5, 15, "Mobile money & phone credit"),
    "food": (8, 15, "Lunch at the market"),
}

# Day-of-week sales multipliers (0=Mon, 6=Sun)
DAY_MULTIPLIER = {0: 1.0, 1: 1.1, 2: 1.5, 3: 1.2, 4: 1.4, 5: 1.8, 6: 0.6}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def weighted_rand(low: float, high: float) -> float:
    """Return a float in [low, high] with slight random variation."""
    return round(random.uniform(low, high), 2)


def spread_hours(target_date: date, count: int) -> list[datetime]:
    """Spread `count` timestamps across market hours (6am–7pm)."""
    base = datetime(target_date.year, target_date.month, target_date.day, 6, 0)
    if count <= 1:
        return [base + timedelta(hours=random.uniform(1, 8))]
    step = timedelta(hours=13 / max(count - 1, 1))
    times = [base + step * i + timedelta(minutes=random.randint(-20, 20)) for i in range(count)]
    return sorted(times)


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

async def seed(db: AsyncSession) -> None:
    # Clear existing data
    log.info("Clearing existing data...")
    await db.execute(delete(Transaction))
    await db.execute(delete(Inventory))
    await db.execute(delete(DailySummary))
    await db.flush()

    today = date.today()
    start_date = today - timedelta(days=13)

    # Running inventory tracker (for WAC calculation)
    inv_state: dict[str, dict] = {
        item: {
            "quantity": cfg["starting_stock"],
            "avg_cost": (cfg["buy_range"][0] + cfg["buy_range"][1]) / 2,
        }
        for item, cfg in AMA_ITEMS.items()
    }

    all_transactions: list[Transaction] = []
    total_tx = 0

    log.info(f"Seeding {(today - start_date).days + 1} days of data for Ama's stall...")

    for day_offset in range(14):
        current_date = start_date + timedelta(days=day_offset)
        weekday = current_date.weekday()
        multiplier = DAY_MULTIPLIER[weekday]

        # Is it a major market/restock day?
        is_restock_day = weekday in (0, 2, 4)  # Mon, Wed, Fri
        is_last_two_days = day_offset >= 12

        day_transactions: list[Transaction] = []

        # ---- PURCHASES ----
        if is_restock_day or day_offset == 0:
            items_to_buy = list(AMA_ITEMS.keys())
            random.shuffle(items_to_buy)
            for item in items_to_buy:
                cfg = AMA_ITEMS[item]
                min_qty, max_qty = cfg["daily_buy"]
                if min_qty == max_qty == 0:
                    continue

                # Skip palm oil and tomatoes on last 2 days to make them low stock
                if is_last_two_days and item in ("palm_oil", "tomatoes"):
                    continue

                qty = round(random.uniform(max_qty * 0.3, max_qty) * multiplier * 0.6)
                if qty < 1:
                    continue

                unit_price = weighted_rand(*cfg["buy_range"])
                total = round(qty * unit_price, 2)
                supplier = random.choice(SUPPLIERS[item])

                # Update WAC
                old_qty = inv_state[item]["quantity"]
                old_avg = inv_state[item]["avg_cost"]
                new_qty = old_qty + qty
                inv_state[item]["avg_cost"] = (old_qty * old_avg + qty * unit_price) / new_qty
                inv_state[item]["quantity"] = new_qty

                day_transactions.append(Transaction(
                    type="purchase",
                    item=item,
                    quantity=float(qty),
                    unit=cfg["unit"],
                    unit_price=unit_price,
                    total_amount=total,
                    currency="GHS",
                    counterparty=supplier,
                    source="voice",
                    language="en",
                    raw_input=f"Bought {qty} {cfg['unit']} of {item} for {unit_price} each from {supplier}",
                    confidence=0.97,
                    created_at=datetime(current_date.year, current_date.month, current_date.day, 6, random.randint(10, 50)),
                    updated_at=datetime(current_date.year, current_date.month, current_date.day, 6, random.randint(10, 50)),
                ))

        # ---- SALES ----
        base_sale_count = int(random.randint(5, 9) * multiplier)
        sale_times = spread_hours(current_date, base_sale_count)

        for i in range(base_sale_count):
            item = random.choices(
                list(AMA_ITEMS.keys()),
                weights=[3, 2, 2, 2, 2],  # rice sells most
            )[0]
            cfg = AMA_ITEMS[item]
            min_qty, max_qty = cfg["daily_sell"]
            if min_qty == max_qty == 0:
                continue

            qty = round(random.uniform(0.5, max_qty), 1)
            if qty < 0.5:
                qty = 1.0

            # Don't sell more than we have (mostly)
            if inv_state[item]["quantity"] < qty and inv_state[item]["quantity"] > 0:
                qty = max(0.5, round(inv_state[item]["quantity"] * 0.4, 1))

            if inv_state[item]["quantity"] <= 0 and random.random() > 0.1:
                continue  # usually skip zero-stock items

            unit_price = weighted_rand(*cfg["sell_range"])
            total = round(qty * unit_price, 2)
            customer = random.choice(CUSTOMERS)

            inv_state[item]["quantity"] = max(0, inv_state[item]["quantity"] - qty)

            ts = sale_times[i] if i < len(sale_times) else sale_times[-1]

            day_transactions.append(Transaction(
                type="sale",
                item=item,
                quantity=float(qty),
                unit=cfg["unit"],
                unit_price=unit_price,
                total_amount=total,
                currency="GHS",
                counterparty=customer,
                source="voice",
                language="en",
                raw_input=f"Sold {qty} {cfg['unit']} of {item} at {unit_price} each" + (f" to {customer}" if customer else ""),
                confidence=0.98,
                created_at=ts,
                updated_at=ts,
            ))

        # ---- EXPENSES ----
        # Transport every day
        exp_times = spread_hours(current_date, 2)
        transport_amt = weighted_rand(10, 22)
        day_transactions.append(Transaction(
            type="expense",
            item="Trotro to Makola Market",
            total_amount=transport_amt,
            currency="GHS",
            category="transport",
            source="voice",
            language="en",
            raw_input=f"Transport cost {transport_amt} cedis",
            confidence=0.99,
            created_at=exp_times[0],
            updated_at=exp_times[0],
        ))

        # Market fee on restock days
        if is_restock_day:
            fee = weighted_rand(5, 10)
            day_transactions.append(Transaction(
                type="expense",
                item="Daily market stall fee",
                total_amount=fee,
                currency="GHS",
                category="market_fee",
                source="voice",
                language="en",
                raw_input=f"Market fee {fee} cedis",
                confidence=0.99,
                created_at=exp_times[1] if len(exp_times) > 1 else exp_times[0],
                updated_at=exp_times[1] if len(exp_times) > 1 else exp_times[0],
            ))

        # Occasional phone / food expenses
        if random.random() < 0.35:
            cat, (lo, hi, desc) = random.choice(list(EXPENSE_CATEGORIES.items()))
            if cat not in ("transport", "market_fee"):
                amt = weighted_rand(lo, hi)
                day_transactions.append(Transaction(
                    type="expense",
                    item=desc,
                    total_amount=amt,
                    currency="GHS",
                    category=cat,
                    source="voice",
                    language="en",
                    raw_input=f"{desc} cost {amt} cedis",
                    confidence=0.95,
                    created_at=spread_hours(current_date, 1)[0],
                    updated_at=spread_hours(current_date, 1)[0],
                ))

        all_transactions.extend(day_transactions)
        total_tx += len(day_transactions)

        rev = sum(t.total_amount for t in day_transactions if t.type == "sale")
        cost = sum(t.total_amount for t in day_transactions if t.type == "purchase")
        exp = sum(t.total_amount for t in day_transactions if t.type == "expense")
        profit = rev - cost - exp

        log.info(
            f"  {current_date} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][weekday]}) "
            f"— {len(day_transactions)} tx | "
            f"rev ₵{rev:.0f} cost ₵{cost:.0f} exp ₵{exp:.0f} "
            f"{'🟢' if profit > 0 else '🔴'} ₵{profit:.0f}"
        )

    # Bulk insert transactions
    db.add_all(all_transactions)
    await db.flush()

    # ---------------------------------------------------------------------------
    # Build inventory table from final inv_state
    # ---------------------------------------------------------------------------
    log.info("Building inventory records...")
    for item, state in inv_state.items():
        cfg = AMA_ITEMS[item]
        quantity = round(state["quantity"], 2)

        # Force low stock for palm_oil and tomatoes
        if item == "palm_oil":
            quantity = 3.0
        elif item == "tomatoes":
            quantity = 1.0

        threshold = {
            "rice": 5.0,
            "onions": 10.0,
            "palm_oil": 5.0,
            "tomatoes": 2.0,
            "plantains": 5.0,
        }[item]

        inv = Inventory(
            item=item,
            quantity=quantity,
            unit=cfg["unit"],
            avg_cost=round(state["avg_cost"], 2),
            last_purchase_price=round(weighted_rand(*cfg["buy_range"]), 2),
            low_stock_threshold=threshold,
            is_low_stock=quantity <= threshold,
            updated_at=datetime.utcnow(),
        )
        db.add(inv)

    await db.flush()
    log.info(f"\n✅ Seeded {total_tx} transactions across 14 days.")
    log.info("   Low stock items: palm_oil (3L), tomatoes (1 crate)")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    db_url = settings.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    AsyncSession_ = async_sessionmaker(engine, expire_on_commit=False)

    async with AsyncSession_() as session:
        async with session.begin():
            await seed(session)

    await engine.dispose()
    log.info("Database ready. Start the app and the dashboard will be pre-populated!")


if __name__ == "__main__":
    asyncio.run(main())
