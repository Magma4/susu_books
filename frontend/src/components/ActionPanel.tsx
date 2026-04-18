"use client";
/**
 * ActionPanel — "What needs action" panel.
 * Shows inventory alerts, restock suggestions, and business insights.
 */

import type { InventoryAlerts, DailySummaryData } from "@/lib/types";
import { formatItemLabel, formatUnitLabel } from "@/lib/display";
import { formatAmount } from "@/styles/theme";

interface ActionPanelProps {
  alerts: InventoryAlerts | null;
  summary: DailySummaryData | null;
  backendOnline: boolean;
  onExportLedger: () => void;
  onBackupData: () => void;
  isExporting?: boolean;
}

export default function ActionPanel({
  alerts,
  summary,
  backendOnline,
  onExportLedger,
  onBackupData,
  isExporting = false,
}: ActionPanelProps) {
  const hasAlerts =
    (alerts?.low_stock_count ?? 0) > 0 ||
    (alerts?.zero_stock_count ?? 0) > 0;

  const allClear = !hasAlerts && backendOnline;

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Needs Action
        </span>
        {hasAlerts && (
          <span className="h-2 w-2 rounded-full bg-warning animate-pulse" />
        )}
      </div>

      <div className="p-3 space-y-2">
        {/* Backend offline warning */}
        {!backendOnline && (
          <AlertCard
            type="error"
            icon="⚡"
            title="AI offline"
            message="The AI service is unavailable. Check the backend and the configured Gemma provider."
          />
        )}

        {/* Zero-stock alerts */}
        {alerts?.zero_stock_items.map((item) => (
          <AlertCard
            key={item.item}
            type="error"
            icon="📦"
            title={`${formatItemLabel(item.item)} — out of stock`}
            message="Restock immediately to avoid missing sales."
          />
        ))}

        {/* Low-stock alerts */}
        {alerts?.low_stock_items.map((item) => (
          <AlertCard
            key={item.item}
            type="warning"
            icon="⚠️"
            title={`${formatItemLabel(item.item)} — low stock`}
            message={`${item.quantity} ${item.unit ? formatUnitLabel(item.unit, item.quantity) : "units"} left (threshold: ${item.threshold}).`}
          />
        ))}

        {/* Positive insights from today's summary */}
        {summary && summary.net_profit > 0 && (
          <InsightCard summary={summary} />
        )}

        {/* Profit margin nudge */}
        {summary &&
          summary.total_revenue > 0 &&
          summary.profit_margin_pct != null &&
          summary.profit_margin_pct < 15 && (
            <AlertCard
              type="info"
              icon="💡"
              title="Low profit margin"
              message={`Today's margin is ${summary.profit_margin_pct.toFixed(1)}%. Try adjusting prices on your top items.`}
            />
          )}

        {/* All clear state */}
        {allClear && !summary?.net_profit && (
          <div className="py-6 text-center">
            <p className="text-3xl mb-2">✅</p>
            <p className="text-sm text-text-secondary">All clear!</p>
            <p className="text-xs text-text-disabled mt-1">
              No stock alerts right now.
            </p>
          </div>
        )}

        {allClear && summary?.net_profit != null && summary.net_profit <= 0 && (
          <div className="py-4 text-center">
            <p className="text-3xl mb-2">✅</p>
            <p className="text-xs text-text-disabled">No stock alerts.</p>
          </div>
        )}

        <div className="pt-2 border-t border-border">
          <p className="text-xs font-semibold uppercase tracking-wide text-text-secondary mb-2">
            Quick Actions
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              type="button"
              onClick={onExportLedger}
              disabled={isExporting}
              className="rounded-xl border border-border px-3 py-2 text-left text-sm font-medium text-text-primary hover:border-primary-900 hover:text-primary-900 transition-colors disabled:opacity-60"
            >
              Export ledger CSV
            </button>
            <button
              type="button"
              onClick={onBackupData}
              disabled={isExporting}
              className="rounded-xl border border-border px-3 py-2 text-left text-sm font-medium text-text-primary hover:border-primary-900 hover:text-primary-900 transition-colors disabled:opacity-60"
            >
              Backup data JSON
            </button>
          </div>
          <p className="text-xs text-text-disabled mt-2">
            Keep a copy of your books before sharing, migrating, or redeploying.
          </p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface AlertCardProps {
  type: "error" | "warning" | "info" | "success";
  icon: string;
  title: string;
  message: string;
}

const alertStyles = {
  error: "bg-red-50 border-red-100 text-danger",
  warning: "bg-accent-light border-amber-100 text-accent-900",
  info: "bg-blue-50 border-blue-100 text-blue-800",
  success: "bg-primary-surface border-primary-100 text-primary-800",
};

function AlertCard({ type, icon, title, message }: AlertCardProps) {
  return (
    <div
      className={`rounded-xl border px-3 py-2.5 ${alertStyles[type]}`}
      role="alert"
    >
      <div className="flex items-start gap-2">
        <span className="text-base flex-shrink-0 mt-0.5">{icon}</span>
        <div>
          <p className="text-sm font-semibold leading-tight">{title}</p>
          <p className="text-xs opacity-80 mt-0.5 leading-snug">{message}</p>
        </div>
      </div>
    </div>
  );
}

function InsightCard({ summary }: { summary: DailySummaryData }) {
  const comp = summary.comparison_to_yesterday;
  const better = comp && comp.profit_change > 0;

  return (
    <div className="rounded-xl border border-primary-100 bg-primary-surface px-3 py-2.5">
      <div className="flex items-start gap-2">
        <span className="text-base flex-shrink-0 mt-0.5">
          {better ? "🚀" : "📊"}
        </span>
        <div>
          <p className="text-sm font-semibold text-primary-900 leading-tight">
            {better
              ? "Great day! You&apos;re up from yesterday"
              : "You&apos;re profitable today"}
          </p>
          <p className="text-xs text-primary-800 opacity-80 mt-0.5">
            Net profit:{" "}
            <span className="font-mono font-semibold">
              {formatAmount(summary.net_profit, "GHS")}
            </span>
            {summary.profit_margin_pct != null &&
              ` (${summary.profit_margin_pct.toFixed(1)}% margin)`}
          </p>
        </div>
      </div>
    </div>
  );
}
