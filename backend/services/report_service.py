"""
Susu Books - Report Service
Computes daily summaries, weekly reports, and lender-friendly credit profiles.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import DailySummary, Transaction
from schemas import TransactionType

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class ReportService:
    """Read-only financial reporting built from the transaction ledger."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _date_range(target_date: date) -> tuple[datetime, datetime]:
        start = datetime.combine(target_date, datetime.min.time())
        end = datetime.combine(target_date, datetime.max.time())
        return start, end

    async def _transactions_for_date(self, target_date: date) -> list[Transaction]:
        start, end = self._date_range(target_date)
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.created_at >= start, Transaction.created_at <= end)
            .order_by(Transaction.created_at.asc(), Transaction.id.asc())
        )
        return list(result.scalars().all())

    async def daily_summary(self, target_date: Optional[date] = None) -> dict[str, object]:
        target_date = target_date or date.today()
        transactions = await self._transactions_for_date(target_date)

        total_revenue = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.sale
        )
        total_cost = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.purchase
        )
        total_expenses = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.expense
        )
        net_profit = total_revenue - total_cost - total_expenses
        transaction_count = len(transactions)

        selling_quantities: dict[str, float] = defaultdict(float)
        for transaction in transactions:
            if transaction.type == TransactionType.sale:
                selling_quantities[transaction.item] += float(transaction.quantity or 0.0)

        top_selling_item: Optional[str] = None
        top_selling_quantity: Optional[float] = None
        if selling_quantities:
            top_selling_item = max(selling_quantities, key=selling_quantities.get)
            top_selling_quantity = round(selling_quantities[top_selling_item], 2)

        yesterday = target_date - timedelta(days=1)
        yesterday_summary = await self._compute_daily_totals(yesterday)
        yesterday_profit = yesterday_summary["net_profit"]
        profit_change_pct: Optional[float] = None
        if yesterday_profit != 0:
            profit_change_pct = round(((net_profit - yesterday_profit) / abs(yesterday_profit)) * 100, 2)

        profit_margin_pct: Optional[float] = None
        if total_revenue > 0:
            profit_margin_pct = round((net_profit / total_revenue) * 100, 2)

        payload = {
            "date": target_date.isoformat(),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "transaction_count": transaction_count,
            "top_selling_item": top_selling_item,
            "top_selling_quantity": top_selling_quantity,
            "profit_change_pct": profit_change_pct,
            "currency": "GHS",
            "profit_margin_pct": profit_margin_pct,
            "comparison_to_yesterday": {
                "yesterday_revenue": round(yesterday_summary["total_revenue"], 2),
                "yesterday_profit": round(yesterday_profit, 2),
                "revenue_change": round(total_revenue - yesterday_summary["total_revenue"], 2),
                "profit_change": round(net_profit - yesterday_profit, 2),
                "revenue_change_pct": (
                    round(
                        ((total_revenue - yesterday_summary["total_revenue"]) / yesterday_summary["total_revenue"]) * 100,
                        2,
                    )
                    if yesterday_summary["total_revenue"] not in {0, 0.0}
                    else None
                ),
            },
        }

        await self._upsert_summary(
            target_date=target_date,
            total_revenue=payload["total_revenue"],
            total_cost=payload["total_cost"],
            total_expenses=payload["total_expenses"],
            net_profit=payload["net_profit"],
            transaction_count=transaction_count,
            top_selling_item=top_selling_item,
            top_selling_quantity=top_selling_quantity,
        )

        return payload

    async def _compute_daily_totals(self, target_date: date) -> dict[str, float]:
        transactions = await self._transactions_for_date(target_date)
        total_revenue = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.sale
        )
        total_cost = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.purchase
        )
        total_expenses = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.expense
        )
        return {
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(total_revenue - total_cost - total_expenses, 2),
        }

    async def _upsert_summary(
        self,
        *,
        target_date: date,
        total_revenue: float,
        total_cost: float,
        total_expenses: float,
        net_profit: float,
        transaction_count: int,
        top_selling_item: Optional[str],
        top_selling_quantity: Optional[float],
    ) -> None:
        result = await self.db.execute(
            select(DailySummary).where(DailySummary.date == target_date)
        )
        summary = result.scalar_one_or_none()
        if summary is None:
            summary = DailySummary(date=target_date)
            self.db.add(summary)

        summary.total_revenue = total_revenue
        summary.total_cost = total_cost
        summary.total_expenses = total_expenses
        summary.net_profit = net_profit
        summary.transaction_count = transaction_count
        summary.top_selling_item = top_selling_item
        summary.top_selling_quantity = top_selling_quantity
        summary.generated_at = utcnow()
        await self.db.flush()

    async def weekly_report(self) -> dict[str, object]:
        today = date.today()
        period_start = today - timedelta(days=6)

        summaries: list[dict[str, object]] = []
        total_transactions = 0
        top_item_revenue: dict[str, float] = defaultdict(float)

        for offset in range(7):
            day = period_start + timedelta(days=offset)
            summary = await self.daily_summary(day)
            summaries.append(summary)
            total_transactions += int(summary["transaction_count"])

            transactions = await self._transactions_for_date(day)
            for transaction in transactions:
                if transaction.type == TransactionType.sale:
                    top_item_revenue[transaction.item] += transaction.total_amount

        total_profit = round(sum(float(summary["net_profit"]) for summary in summaries), 2)
        avg_daily_profit = round(total_profit / 7, 2)
        total_revenue = round(sum(float(summary["total_revenue"]) for summary in summaries), 2)
        total_cost = round(sum(float(summary["total_cost"]) for summary in summaries), 2)
        total_expenses = round(sum(float(summary["total_expenses"]) for summary in summaries), 2)

        best_summary = max(summaries, key=lambda item: float(item["net_profit"]))
        worst_summary = min(summaries, key=lambda item: float(item["net_profit"]))

        daily_trend = [
            {
                "date": str(summary["date"]),
                "revenue": summary["total_revenue"],
                "cost": summary["total_cost"],
                "expenses": summary["total_expenses"],
                "profit": summary["net_profit"],
                "transaction_count": summary["transaction_count"],
            }
            for summary in summaries
        ]

        top_items = sorted(
            (
                {"item": item, "revenue": round(revenue, 2)}
                for item, revenue in top_item_revenue.items()
            ),
            key=lambda payload: payload["revenue"],
            reverse=True,
        )[:3]

        return {
            "period_start": period_start.isoformat(),
            "period_end": today.isoformat(),
            "currency": "GHS",
            "start_date": period_start.isoformat(),
            "end_date": today.isoformat(),
            "total_revenue": total_revenue,
            "total_cost": total_cost,
            "total_expenses": total_expenses,
            "total_profit": total_profit,
            "avg_daily_profit": avg_daily_profit,
            "total_transactions": total_transactions,
            "best_day": {
                "date": best_summary["date"],
                "profit": best_summary["net_profit"],
            },
            "worst_day": {
                "date": worst_summary["date"],
                "profit": worst_summary["net_profit"],
            },
            "top_items": top_items,
            "top_items_by_revenue": top_items,
            "daily_profits": [float(summary["net_profit"]) for summary in summaries],
            "daily_trend": daily_trend,
        }

    async def export_credit_profile(self, days: int = 180) -> dict[str, object]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.created_at >= start_dt, Transaction.created_at <= end_dt)
            .order_by(Transaction.created_at.asc(), Transaction.id.asc())
        )
        transactions = list(result.scalars().all())

        total_revenue = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.sale
        )
        total_cost = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.purchase
        )
        total_expenses = sum(
            transaction.total_amount
            for transaction in transactions
            if transaction.type == TransactionType.expense
        )
        total_profit = total_revenue - total_cost - total_expenses
        total_transactions = len(transactions)

        avg_daily_revenue = round(total_revenue / days, 2)
        avg_daily_profit = round(total_profit / days, 2)

        active_days = len(
            {
                transaction.created_at.date()
                for transaction in transactions
                if transaction.type in {TransactionType.purchase, TransactionType.sale, TransactionType.expense}
            }
        )
        consistency_score = round(active_days / days, 4)

        item_revenue: dict[str, float] = defaultdict(float)
        for transaction in transactions:
            if transaction.type == TransactionType.sale:
                item_revenue[transaction.item] += transaction.total_amount
        top_categories = sorted(
            (
                {"category": item, "revenue": round(revenue, 2)}
                for item, revenue in item_revenue.items()
            ),
            key=lambda payload: payload["revenue"],
            reverse=True,
        )[:5]

        monthly_breakdown: dict[str, dict[str, object]] = defaultdict(
            lambda: {
                "month": "",
                "revenue": 0.0,
                "cost": 0.0,
                "expenses": 0.0,
                "profit": 0.0,
                "transactions": 0,
            }
        )

        for transaction in transactions:
            month_key = transaction.created_at.strftime("%Y-%m")
            monthly_breakdown[month_key]["month"] = month_key
            monthly_breakdown[month_key]["transactions"] = int(monthly_breakdown[month_key]["transactions"]) + 1
            if transaction.type == TransactionType.sale:
                monthly_breakdown[month_key]["revenue"] = float(monthly_breakdown[month_key]["revenue"]) + transaction.total_amount
            elif transaction.type == TransactionType.purchase:
                monthly_breakdown[month_key]["cost"] = float(monthly_breakdown[month_key]["cost"]) + transaction.total_amount
            elif transaction.type == TransactionType.expense:
                monthly_breakdown[month_key]["expenses"] = float(monthly_breakdown[month_key]["expenses"]) + transaction.total_amount

        for payload in monthly_breakdown.values():
            revenue = float(payload["revenue"])
            cost = float(payload["cost"])
            expenses = float(payload["expenses"])
            payload["revenue"] = round(revenue, 2)
            payload["cost"] = round(cost, 2)
            payload["expenses"] = round(expenses, 2)
            payload["profit"] = round(revenue - cost - expenses, 2)

        risk_level = "high"
        if consistency_score >= 0.7 and avg_daily_profit > 0:
            risk_level = "low"
        elif consistency_score >= 0.4:
            risk_level = "medium"

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "period_days": days,
            "avg_daily_revenue": avg_daily_revenue,
            "avg_daily_profit": avg_daily_profit,
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "total_transactions": total_transactions,
            "active_days": active_days,
            "consistency_score": consistency_score,
            "top_categories": top_categories,
            "monthly_breakdown": sorted(monthly_breakdown.values(), key=lambda payload: payload["month"]),
            "risk_level": risk_level,
        }
