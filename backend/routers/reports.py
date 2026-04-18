"""
Susu Books - Reports Router
Daily summaries, weekly reports, and credit profile export.
"""

from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from schemas import CreditProfileResponse, DailySummaryResponse, WeeklyReportResponse
from services.report_service import ReportService

router = APIRouter(prefix="/api", tags=["reports"])


@router.get("/summary/daily", response_model=DailySummaryResponse)
async def daily_summary(
    date: Optional[str] = Query(
        None,
        description="Date in YYYY-MM-DD format. Defaults to today.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Return daily financial summary for the given date (default: today).
    Includes revenue, costs, expenses, net profit, top-selling item,
    and comparison to yesterday.
    """
    svc = ReportService(db)

    parsed_date: Optional[date_type] = None
    if date:
        try:
            parsed_date = date_type.fromisoformat(date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date: {date}. Use YYYY-MM-DD.",
            )

    summary = await svc.daily_summary(parsed_date)
    return summary


@router.get("/summary/weekly", response_model=WeeklyReportResponse)
async def weekly_report(
    db: AsyncSession = Depends(get_db),
):
    """
    Return a 7-day rolling report covering today and the previous 6 days.
    Includes daily trend, totals, best/worst days, and top items by revenue.
    """
    svc = ReportService(db)
    report = await svc.weekly_report()
    return report


@router.get("/export/credit-profile", response_model=CreditProfileResponse)
async def credit_profile(
    days: int = Query(
        180,
        ge=1,
        le=730,
        description="Number of past days to include (default 180, max 730).",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Export a structured credit profile for financial assessment.
    Returns average daily revenue/profit, consistency score, monthly breakdown,
    and a simple risk level indicator.
    """
    svc = ReportService(db)
    profile = await svc.export_credit_profile(days)
    return profile
