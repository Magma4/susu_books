"use client";
/**
 * InventoryPanel — Grid of current inventory items with stock level indicators.
 * Highlights low-stock and zero-stock items with amber/red badges.
 */

import type { InventoryItem } from "@/lib/types";
import { formatAmount } from "@/styles/theme";

interface InventoryPanelProps {
  items: InventoryItem[];
  isLoading?: boolean;
}

export default function InventoryPanel({
  items,
  isLoading = false,
}: InventoryPanelProps) {
  const lowStockItems = items.filter((i) => i.is_low_stock && i.quantity > 0);
  const zeroStockItems = items.filter((i) => i.quantity <= 0);
  const healthyItems = items.filter((i) => !i.is_low_stock);

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-between">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          Inventory
        </span>
        <div className="flex items-center gap-2">
          {zeroStockItems.length > 0 && (
            <span className="text-2xs font-semibold bg-red-100 text-danger px-2 py-0.5 rounded-full">
              {zeroStockItems.length} out of stock
            </span>
          )}
          {lowStockItems.length > 0 && (
            <span className="text-2xs font-semibold bg-accent-light text-accent-800 px-2 py-0.5 rounded-full">
              {lowStockItems.length} low
            </span>
          )}
        </div>
      </div>

      {isLoading ? (
        <SkeletonList />
      ) : items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="divide-y divide-border">
          {/* Zero-stock items first (critical) */}
          {zeroStockItems.map((item) => (
            <InventoryRow key={item.id} item={item} />
          ))}
          {/* Low-stock items */}
          {lowStockItems.map((item) => (
            <InventoryRow key={item.id} item={item} />
          ))}
          {/* Healthy items */}
          {healthyItems.map((item) => (
            <InventoryRow key={item.id} item={item} />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function InventoryRow({ item }: { item: InventoryItem }) {
  const isZero = item.quantity <= 0;
  const isLow = item.is_low_stock && !isZero;

  // Stock fill percentage (capped at 100%)
  const fillPct = isZero
    ? 0
    : Math.min(
        ((item.quantity - item.low_stock_threshold) /
          (item.quantity + item.low_stock_threshold)) *
          100 +
          50,
        100
      );

  return (
    <div className="px-4 py-3 flex items-center gap-3">
      {/* Status dot */}
      <div
        className={`h-2 w-2 rounded-full flex-shrink-0 ${
          isZero ? "bg-danger" : isLow ? "bg-warning" : "bg-primary-light"
        }`}
      />

      {/* Name + unit */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-text-primary capitalize truncate">
          {item.item}
        </p>
        {item.avg_cost != null && (
          <p className="text-2xs text-text-secondary">
            avg cost {formatAmount(item.avg_cost, "GHS")} / {item.unit ?? "unit"}
          </p>
        )}
      </div>

      {/* Quantity + mini bar */}
      <div className="text-right flex-shrink-0">
        <p
          className={`font-mono font-semibold text-sm ${
            isZero ? "text-danger" : isLow ? "text-warning" : "text-text-primary"
          }`}
        >
          {item.quantity.toLocaleString()}
          {item.unit ? (
            <span className="font-sans font-normal text-text-secondary ml-1 text-xs">
              {item.unit}
            </span>
          ) : null}
        </p>

        {/* Mini stock bar */}
        <div className="mt-1 h-1 w-16 bg-gray-100 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              isZero ? "bg-danger" : isLow ? "bg-warning" : "bg-primary-light"
            }`}
            style={{ width: `${fillPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="px-4 py-8 text-center">
      <p className="text-4xl mb-2">📦</p>
      <p className="text-sm text-text-secondary">No inventory yet.</p>
      <p className="text-xs text-text-disabled mt-1">
        Record a purchase to start tracking stock.
      </p>
    </div>
  );
}

function SkeletonList() {
  return (
    <div className="divide-y divide-border">
      {[0, 1, 2].map((i) => (
        <div key={i} className="px-4 py-3 flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-gray-200 animate-pulse flex-shrink-0" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-24 bg-gray-200 rounded animate-pulse" />
            <div className="h-2 w-16 bg-gray-100 rounded animate-pulse" />
          </div>
          <div className="h-4 w-12 bg-gray-200 rounded animate-pulse" />
        </div>
      ))}
    </div>
  );
}
