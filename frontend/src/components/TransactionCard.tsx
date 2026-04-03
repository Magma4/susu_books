"use client";
/**
 * TransactionCard — A single transaction row in the live ledger feed.
 * Slides in from the top when it first renders (CSS animation).
 */

import { txColors, formatAmount, formatTime, relativeTime } from "@/styles/theme";
import type { Transaction } from "@/lib/types";

interface TransactionCardProps {
  transaction: Transaction;
  /** When true, applies the slide-in animation (new transactions) */
  isNew?: boolean;
}

export default function TransactionCard({
  transaction: t,
  isNew = false,
}: TransactionCardProps) {
  const style = txColors[t.type];

  return (
    <div
      className={`
        flex items-center gap-3 px-3 py-3 rounded-xl border bg-white
        transition-shadow hover:shadow-card-hover cursor-default select-none
        ${style.border}
        ${isNew ? "animate-slide-in" : ""}
      `}
    >
      {/* Type icon */}
      <div
        className={`
          h-9 w-9 rounded-full flex items-center justify-center flex-shrink-0
          ${style.bg} ${style.text}
        `}
      >
        <span className="text-lg font-bold leading-none">{style.icon}</span>
      </div>

      {/* Main content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          {/* Item + counterparty */}
          <div className="min-w-0">
            <p className="font-semibold text-text-primary text-sm capitalize truncate">
              {t.item}
            </p>
            {(t.counterparty || t.category) && (
              <p className="text-2xs text-text-secondary truncate mt-0.5">
                {t.counterparty ?? t.category}
              </p>
            )}
          </div>

          {/* Amount + time */}
          <div className="text-right flex-shrink-0">
            <p className={`font-mono font-semibold text-sm ${style.amount}`}>
              {formatAmount(t.total_amount, t.currency)}
            </p>
            <p className="text-2xs text-text-secondary mt-0.5">
              {relativeTime(t.created_at)}
            </p>
          </div>
        </div>

        {/* Quantity/unit row */}
        {t.quantity != null && t.unit && (
          <p className="text-2xs text-text-secondary mt-1">
            {t.quantity} {t.unit}
            {t.unit_price != null
              ? ` × ${formatAmount(t.unit_price, t.currency)}`
              : ""}
          </p>
        )}
      </div>

      {/* Source badge */}
      <div className="flex-shrink-0">
        <SourceBadge source={t.source} />
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SourceBadge({ source }: { source: Transaction["source"] }) {
  if (source === "voice") {
    return (
      <span className="text-text-disabled" title="Recorded via voice">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      </span>
    );
  }
  if (source === "photo") {
    return (
      <span className="text-text-disabled" title="Extracted from photo">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
          <circle cx="12" cy="13" r="4" />
        </svg>
      </span>
    );
  }
  return null;
}
