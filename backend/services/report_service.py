"""
Susu Books - Report Service
Generates daily summaries, weekly reports, and credit profiles.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from models import Transaction, DailySummary
from schemas import TransactionType

logger = logging.getLogger(__name__)


class ReportService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _date_range(self, target_date: date) -> tuple[datetime, datetime]:
        start = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0)
        end = datetime(target_date.year, target_date.month, target_date.day, 23, 59, 59, 999999)
        return start, end

    async def _transactions_for_date(self, target_date: date) -> list[Transaction]:
        start, end = self._date_range(target_date)
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.created_at >= start)
            .where(Transaction.created_at <= end)
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Daily Summary
    # ------------------------------------------------------------------

    async def daily_summary(self, target_date: Optional[date] = None) -> dict:
        """
        Compute a full daily summary.
        Caches the result in daily_summaries table.
        Returns comparison-to-yesterday metrics.
        """
        if target_date is None:
            target_date = date.today()

        transactions = await self._transactions_for_date(target_date)

        total_revenue = sum(
            t.total_amount for t in transactions if t.type == TransactionType.sale
        )
        total_cost = sum(
            t.total_amount for t in transactions if t.type == TransactionType.purchase
        )
        total_expenses = sum(
            t.total_amount for t in transactions if t.type == TransactionType.expense
        )
        net_profit = total_revenue - total_cost - total_expenses
        transaction_count = len(transactions)

        # Find top-selling item by revenue
        sales = [t for t in transactions if t.type == TransactionType.sale]
        item_revenue: dict[str, float] = defaultdict(float)
        for t in sales:
            item_revenue[t.item] += t.total_amount
        top_selling_item = max(item_revenue, key=item_revenue.get) if item_revenue else None

        # Persist summary
        await self._upsert_summary(
            target_date, total_revenue, total_cost, total_expenses,
            net_profit, transaction_count, top_selling_item
        )

        # Comparison to yesterday
        yesterday = target_date - timedelta(days=1)
        yesterday_txns = await self._transactions_for_date(yesterday)
        yesterday_revenue = sum(
            t.total_amount for t in yesterday_txns if t.type == TransactionType.sale
        )
        yesterday_profit = (
            sum(t.total_amount for t in yesterday_txns if t.type == TransactionType.sale)
            - sum(t.total_amount for t in yesterday_txns if t.type == TransactionType.purchase)
            - sum(t.total_amount for t in yesterday_txns if t.type == TransactionType.expense)
        )

        profit_margin_pct = (net_profit / total_revenue * 100) if total_revenue > 0 else None

        comparison = {
            "yesterday_revenue": round(yesterday_revenue, 2),
            "yesterday_profit": round(yesterday_profit, 2),
            "revenue_change": round(total_revenue - yesterday_revenue, 2),
            "profit_change": round(net_profit - yesterday_profit, 2),
            "revenue_change_pct": (
                round((total_revenue - yesterday_revenue) / yesterday_revenue * 100, 1)
                if yesterday_revenue > 0 else None
            ),
        }

        return {
            "date": target_date.isoformat(),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_expenses": round(total_expenses, 2),
            "net_profit": round(net_profit, 2),
            "transaction_count": transaction_count,
            "top_selling_item": top_selling_item,
            "profit_margin_pct": round(profit_margin_pct, 1) if profit_margin_pct is not None else None,
            "comparison_to_yesterday": comparison,
        }

    async def _upsert_summary(
        self,
        target_date: date,
        total_revenue: float,
        total_cost: float,
        total_expenses: float,
        net_profit: float,
        transaction_count: int,
        top_selling_item: Optional[str],
    ) -> None:
        """Insert or replace the daily_summaries row for target_date."""
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
        summary.generated_at = datetime.utcnow()
        await self.db.flush()

    # ------------------------------------------------------------------
    # Weekly Report
    # ------------------------------------------------------------------

    async def weekly_report(self) -> dict:
        """
        Compute last 7 calendar days (today inclusive).
        Returns daily profit trend, best/worst days, top items by revenue, totals.
        """
        today = date.today()
        start_date = today - timedelta(days=6)

        daily_trend = []
        total_revenue = 0.0
        total_cost = 0.0
        total_expenses = 0.0
        item_revenue: dict[str, float] = defaultdict(float)

        best_day: Optional[dict] = None
        worst_day: Optional[dict] = None

        for offset in range(7):
            day = start_date + timedelta(days=offset)
            txns = await self._transactions_for_date(day)

            day_revenue = sum(t.total_amount for t in txns if t.type == TransactionType.sale)
            day_cost = sum(t.total_amount for t in txns if t.type == TransactionType.purchase)
            day_expenses = sum(t.total_amount for t in txns if t.type == TransactionType.expense)
            day_profit = day_revenue - day_cost - day_expenses

            total_revenue += day_revenue
            total_cost += day_cost
            total_expenses += day_expenses

            for t in txns:
                if t.type == TransactionType.sale:
                    item_revenue[t.item] += t.total_amount

            day_data = {
                "date": day.isoformat(),
                "revenue": round(day_revenue, 2),
                "cost": round(day_cost, 2),
                "expenses": round(day_expenses, 2),
                "profit": round(day_profit, 2),
                "transaction_count": len(txns),
            }
            daily_trend.append(day_data)

            if best_day is None or day_profit > best_day["profit"]:
                best_day = day_data
            if worst_day is None or day_profit < worst_day["profit"]:
                worst_day = day_data

        total_profit = total_revenue - total_cost - total_expenses
        avg_daily_profit = total_profit / 7

        top_items = sorted(
            [{"item": k, "revenue": round(v, 2)} for k, v in item_revenue.items()],
            key=lambda x: x["revenue"],
            reverse=True,
        )[:5]

        return {
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "total_revenue": round(total_revenue, 2),
            "total_cost": round(total_cost, 2),
            "total_expenses": round(total_expenses, 2),
            "total_profit": round(total_profit, 2),
            "avg_daily_profit": round(avg_daily_profit, 2),
            "best_day": best_day,
            "worst_day": worst_day,
            "daily_trend": daily_trend,
            "top_items_by_revenue": top_items,
        }

    # ------------------------------------------------------------------
    # Credit Profile
    # ------------------------------------------------------------------

    async def export_credit_profile(self, days: int = 180) -> dict:
        """
        Aggregated financial summary for creditworthiness assessment.
        Computes consistency score: % of days in period with any revenue.
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        start_dt = datetime(start_date.year, start_date.month, start_date.day)
        end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59)

        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.created_at >= start_dt)
            .where(Transaction.created_at <= end_dt)
        )
        all_txns = list(result.scalars().all())

        total_revenue = sum(
            t.total_amount for t in all_txns if t.type == TransactionType.sale
        )
        total_cost = sum(
            t.total_amount for t in all_txns if t.type == TransactionType.purchase
        )
        total_expenses = sum(
            t.total_amount for t in all_txns if t.type == TransactionType.expense
        )
        total_profit = total_revenue - total_cost - total_expenses
        total_transactions = len(all_txns)

        avg_daily_revenue = total_revenue / days
        avg_daily_profit = total_profit / days

        # Consistency score: percentage of days with at least one sale
        days_with_sales: set[date] = set()
        for t in all_txns:
            if t.type == TransactionType.sale:
                days_with_sales.add(t.created_at.date())
        consistency_score = (len(days_with_sales) / days) * 100

        # Top expense categories
        category_totals: dict[str, float] = defaultdict(float)
        for t in all_txns:
            if t.type == TransactionType.expense and t.category:
                category_totals[t.category] += t.total_amount
        top_categories = sorted(
            [{"category": k, "total": round(v, 2)} for k, v in category_totals.items()],
            key=lambda x: x["total"],
            reverse=True,
        )[:10]

        # Monthly breakdown
        monthly: dict[str, dict] = defaultdict(
            lambda: {"revenue": 0.0, "cost": 0.0, "expenses": 0.0, "profit": 0.0, "transactions": 0}
        )
        for t in all_txns:
            key = t.created_at.strftime("%Y-%m")
            if t.type == TransactionType.sale:
                monthly[key]["revenue"] += t.total_amount
            elif t.type == TransactionType.purchase:
                monthly[key]["cost"] += t.total_amount
            elif t.type == TransactionType.expense:
                monthly[key]["expenses"] += t.total_amount
            monthly[key]["transactions"] += 1
        for k, v in monthly.items():
            v["profit"] = round(v["revenue"] - v["cost"] - v["expenses"], 2)
            v["month"] = k

        monthly_breakdown = sorted(monthly.values(), key=lambda x: x["month"])

        # Simple risk level
        if consistency_score >= 70 and avg_daily_profit > 0:
            risk_level = "low"
        elif consistency_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "period_days": days,
            "avg_daily_revenue": round(avg_daily_revenue, 2),
            "avg_daily_profit": round(avg_daily_profit, 2),
            "total_revenue": round(total_revenue, 2),
            "total_profit": round(total_profit, 2),
            "total_transactions": total_transactions,
            "consistency_score": round(consistency_score, 1),
            "top_categories": top_categories,
            "monthly_breakdown": monthly_breakdown,
            "risk_level": risk_level,
        }
