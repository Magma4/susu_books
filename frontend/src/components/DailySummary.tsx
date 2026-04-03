"use client";
/**
 * DailySummary — Today's P&L summary card.
 * Shows Revenue, Costs, Expenses, Net Profit with count-up animation on update.
 */

import { useEffect, useRef, useState } from "react";
import { formatAmount } from "@/styles/theme";
import type { DailySummaryData } from "@/lib/types";

interface DailySummaryProps {
  data: DailySummaryData | null;
  currency?: string;
  isLoading?: boolean;
}

export default function DailySummary({
  data,
  currency = "GHS",
  isLoading = false,
}: DailySummaryProps) {
  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Today&apos;s Results
        </span>
        {data?.top_selling_item && (
          <span className="text-2xs text-text-secondary bg-primary-surface px-2 py-0.5 rounded-full">
            🏆 {data.top_selling_item}
          </span>
        )}
      </div>

      {isLoading || !data ? (
        <SkeletonGrid />
      ) : (
        <div className="p-4 grid grid-cols-2 gap-3">
          <SummaryCell
            label="Revenue"
            value={data.total_revenue}
            currency={currency}
            colorClass="text-primary-800"
            bgClass="bg-primary-surface"
            icon="↑"
          />
          <SummaryCell
            label="Costs"
            value={data.total_cost}
            currency={currency}
            colorClass="text-accent-800"
            bgClass="bg-accent-light"
            icon="↓"
          />
          <SummaryCell
            label="Expenses"
            value={data.total_expenses}
            currency={currency}
            colorClass="text-danger"
            bgClass="bg-red-50"
            icon="→"
          />
          <SummaryCell
            label="Net Profit"
            value={data.net_profit}
            currency={currency}
            colorClass={data.net_profit >= 0 ? "text-primary-900" : "text-danger"}
            bgClass={data.net_profit >= 0 ? "bg-primary-surface" : "bg-red-50"}
            icon="="
            isBold
          />
        </div>
      )}

      {/* Comparison to yesterday */}
      {data?.comparison_to_yesterday && (
        <YesterdayComparison
          comparison={data.comparison_to_yesterday}
          currency={currency}
        />
      )}

      {/* Transaction count */}
      {data && (
        <div className="px-4 pb-3 text-center">
          <span className="text-2xs text-text-secondary">
            {data.transaction_count} transaction
            {data.transaction_count !== 1 ? "s" : ""} today
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface SummaryCellProps {
  label: string;
  value: number;
  currency: string;
  colorClass: string;
  bgClass: string;
  icon: string;
  isBold?: boolean;
}

function SummaryCell({
  label,
  value,
  currency,
  colorClass,
  bgClass,
  icon,
  isBold,
}: SummaryCellProps) {
  const animatedValue = useCountUp(value, 600);

  return (
    <div
      className={`
        rounded-xl p-3 flex flex-col gap-1 ${bgClass}
        ${isBold ? "border-2 border-current " + colorClass.replace("text-", "border-") : ""}
      `}
    >
      <div className="flex items-center gap-1.5">
        <span className={`text-base font-bold ${colorClass}`}>{icon}</span>
        <span className="text-2xs font-semibold text-text-secondary uppercase tracking-wide">
          {label}
        </span>
      </div>
      <p
        className={`
          font-mono font-semibold text-sm leading-tight ${colorClass}
          ${isBold ? "text-base" : ""}
        `}
      >
        {formatAmount(animatedValue, currency)}
      </p>
    </div>
  );
}

function YesterdayComparison({
  comparison,
  currency,
}: {
  comparison: NonNullable<DailySummaryData["comparison_to_yesterday"]>;
  currency: string;
}) {
  const isUp = comparison.profit_change >= 0;
  return (
    <div className="px-4 pb-3 border-t border-border pt-2 flex items-center justify-between">
      <span className="text-2xs text-text-secondary">vs yesterday</span>
      <span
        className={`text-2xs font-semibold ${
          isUp ? "text-primary-800" : "text-danger"
        }`}
      >
        {isUp ? "▲" : "▼"}{" "}
        {formatAmount(Math.abs(comparison.profit_change), currency)}
        {comparison.revenue_change_pct != null && (
          <span className="font-normal ml-1 opacity-70">
            ({comparison.revenue_change_pct > 0 ? "+" : ""}
            {comparison.revenue_change_pct.toFixed(1)}%)
          </span>
        )}
      </span>
    </div>
  );
}

function SkeletonGrid() {
  return (
    <div className="p-4 grid grid-cols-2 gap-3">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-16 rounded-xl bg-gray-100 animate-pulse"
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Count-up animation hook (private to this file)
// ---------------------------------------------------------------------------

function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

function useCountUp(target: number, duration = 600): number {
  const [current, setCurrent] = useState(target);
  const prevTargetRef = useRef(target);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const from = prevTargetRef.current;
    prevTargetRef.current = target;

    if (from === target) return;

    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      setCurrent(from + (target - from) * easeOut(progress));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        setCurrent(target);
      }
    };
    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target, duration]);

  return current;
}
