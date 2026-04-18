"use client";
/**
 * TransactionFeed — Scrollable live ledger of today's transactions.
 * New transactions slide in from the top with animation.
 * Groups by transaction type for quick scanning.
 */

import { useEffect, useRef, useState } from "react";
import TransactionCard from "./TransactionCard";
import type { Transaction } from "@/lib/types";

interface TransactionFeedProps {
  transactions: Transaction[];
  isLoading?: boolean;
}

export default function TransactionFeed({
  transactions,
  isLoading = false,
}: TransactionFeedProps) {
  // Track IDs of recently added transactions for slide-in animation
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const prevCountRef = useRef(transactions.length);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prev = prevCountRef.current;
    const curr = transactions.length;
    if (curr > prev) {
      // Mark the newest transactions as "new" for animation
      const freshIds = transactions.slice(0, curr - prev).map((t) => t.id);
      setNewIds(new Set(freshIds));
      // Clear animation flag after it plays
      const timer = setTimeout(() => setNewIds(new Set()), 600);
      return () => clearTimeout(timer);
    }
    prevCountRef.current = curr;
  }, [transactions]);

  // Today's date string for filtering display label
  const todayLabel = new Date().toLocaleDateString("en-GH", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  // Tally by type
  const salesCount = transactions.filter((t) => t.type === "sale").length;
  const purchasesCount = transactions.filter((t) => t.type === "purchase").length;
  const expensesCount = transactions.filter((t) => t.type === "expense").length;

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
              Today&apos;s Ledger
            </span>
            <p className="text-xs text-text-disabled mt-0.5">{todayLabel}</p>
          </div>

          {/* Type summary pills */}
          {transactions.length > 0 && (
            <div className="flex items-center gap-1.5">
              {salesCount > 0 && (
                <TypePill count={salesCount} label="sales" colorClass="bg-primary-surface text-primary-800" />
              )}
              {purchasesCount > 0 && (
                <TypePill count={purchasesCount} label="buys" colorClass="bg-accent-light text-accent-800" />
              )}
              {expensesCount > 0 && (
                <TypePill count={expensesCount} label="expenses" colorClass="bg-red-50 text-danger" />
              )}
            </div>
          )}
        </div>
      </div>

      {/* Transaction list */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overscroll-contain"
        style={{ minHeight: "300px", maxHeight: "calc(100vh - 320px)" }}
      >
        {isLoading ? (
          <SkeletonList />
        ) : transactions.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="p-3 space-y-2">
            {transactions.map((tx) => (
              <TransactionCard
                key={tx.id}
                transaction={tx}
                isNew={newIds.has(tx.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function TypePill({
  count,
  label,
  colorClass,
}: {
  count: number;
  label: string;
  colorClass: string;
}) {
  return (
    <span
      className={`text-2xs font-semibold px-2 py-0.5 rounded-full ${colorClass}`}
    >
      {count} {label}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-48 px-6 text-center">
      <div className="text-5xl mb-3">🛒</div>
      <p className="text-sm font-semibold text-text-secondary">
        No transactions yet today
      </p>
      <p className="text-xs text-text-disabled mt-1.5 leading-relaxed">
        Tap the microphone and say something like:
        <br />
        <em className="text-text-secondary">
          &ldquo;I sold 2 bags of rice for 200 cedis each&rdquo;
        </em>
      </p>
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="p-3 space-y-2">
      {[0, 1, 2, 3].map((i) => (
        <div
          key={i}
          className="flex items-center gap-3 px-3 py-3 rounded-xl border border-border"
        >
          <div className="h-9 w-9 rounded-full bg-gray-100 animate-pulse flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-3 w-32 bg-gray-100 rounded animate-pulse" />
            <div className="h-2 w-20 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="h-4 w-16 bg-gray-100 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}
