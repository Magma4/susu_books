"use client";
/**
 * TransactionCard — A single transaction row in the live ledger feed.
 * Slides in from the top when it first renders (CSS animation).
 * Features hover-active editing and deleting triggers.
 */

import { txColors, formatAmount, relativeTime } from "@/styles/theme";
import type { Transaction } from "@/lib/types";
import {
  formatTransactionSubtitle,
  formatTransactionTitle,
  formatUnitLabel,
} from "@/lib/display";

interface TransactionCardProps {
  transaction: Transaction;
  isNew?: boolean;
  onEdit: (tx: Transaction) => void;
  onDelete: (tx: Transaction) => void;
}

export default function TransactionCard({
  transaction: t,
  isNew = false,
  onEdit,
  onDelete,
}: TransactionCardProps) {
  const style = txColors[t.type];
  const title = formatTransactionTitle(t);
  const subtitle = formatTransactionSubtitle(t);
  const unitLabel = t.unit ? formatUnitLabel(t.unit, t.quantity) : null;

  return (
    <div
      className={`
        flex items-center gap-3 px-3 py-3 rounded-xl border bg-white
        transition-all duration-200 hover:shadow-card-hover hover:border-gray-300 group
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
            <p className="font-semibold text-text-primary text-sm truncate">
              {title}
            </p>
            {subtitle && (
              <p className="text-2xs text-text-secondary truncate mt-0.5">
                {subtitle}
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
        {t.quantity != null && unitLabel && (
          <p className="text-2xs text-text-secondary mt-1">
            {t.quantity} {unitLabel}
            {t.unit_price != null
              ? ` × ${formatAmount(t.unit_price, t.currency)}`
              : ""}
          </p>
        )}
      </div>

      {/* Badges / Hover Actions */}
      <div className="flex items-center gap-1.5 flex-shrink-0 ml-1">
        {/* Source Badge — hides on card hover to reveal actions for touch/mouse */}
        <div className="group-hover:hidden transition-all duration-150 flex items-center justify-center">
          <SourceBadge source={t.source} />
        </div>

        {/* Action controls — revealed on card hover */}
        <div className="hidden group-hover:flex items-center gap-1 transition-all duration-150">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit(t);
            }}
            aria-label="Edit transaction"
            className="p-1.5 text-text-disabled hover:text-primary-700 hover:bg-primary-surface rounded-lg transition-all duration-150 active:scale-90"
          >
            <PencilIcon />
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(t);
            }}
            aria-label="Delete transaction"
            className="p-1.5 text-text-disabled hover:text-danger hover:bg-red-50 rounded-lg transition-all duration-150 active:scale-90"
          >
            <TrashIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components & Icons
// ---------------------------------------------------------------------------

function PencilIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

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
