"use client";
/**
 * InventoryPanel — Grid of current inventory items with stock level indicators.
 * Highlights low-stock and zero-stock items with amber/red badges.
 * Includes inline editor for adjusting stock levels directly and deleting items.
 */

import { useState, useEffect } from "react";
import InventorySetupForm from "@/components/InventorySetupForm";
import type { InventoryItem } from "@/lib/types";
import { formatItemLabel, formatUnitLabel } from "@/lib/display";
import { formatAmount } from "@/styles/theme";
import { deleteInventoryItem, updateInventoryItem } from "@/lib/api";

interface InventoryPanelProps {
  items: InventoryItem[];
  isLoading?: boolean;
  onInventoryChanged?: () => Promise<void> | void;
  onNotify?: (type: "success" | "error", message: string) => void;
  defaultCurrency?: string;
}

export default function InventoryPanel({
  items,
  isLoading = false,
  onInventoryChanged,
  onNotify,
  defaultCurrency = "GHS",
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

      <InventorySetupForm onInventoryChanged={onInventoryChanged} onNotify={onNotify} />

      {isLoading ? (
        <SkeletonList />
      ) : items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="divide-y divide-border">
          {/* Zero-stock items first (critical) */}
          {zeroStockItems.map((item) => (
            <InventoryRow
              key={item.id}
              item={item}
              onInventoryChanged={onInventoryChanged}
              onNotify={onNotify}
              defaultCurrency={defaultCurrency}
            />
          ))}
          {/* Low-stock items */}
          {lowStockItems.map((item) => (
            <InventoryRow
              key={item.id}
              item={item}
              onInventoryChanged={onInventoryChanged}
              onNotify={onNotify}
              defaultCurrency={defaultCurrency}
            />
          ))}
          {/* Healthy items */}
          {healthyItems.map((item) => (
            <InventoryRow
              key={item.id}
              item={item}
              onInventoryChanged={onInventoryChanged}
              onNotify={onNotify}
              defaultCurrency={defaultCurrency}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Action Icons
// ---------------------------------------------------------------------------

const PencilIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
    <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L6.832 19.82a4.5 4.5 0 01-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 011.13-1.897L16.863 4.487zm0 0L19.5 7.125" />
  </svg>
);

const TrashIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
  </svg>
);

// ---------------------------------------------------------------------------
// Row Component with Inline Editor and Delete
// ---------------------------------------------------------------------------

interface InventoryRowProps {
  item: InventoryItem;
  onInventoryChanged?: () => Promise<void> | void;
  onNotify?: (type: "success" | "error", message: string) => void;
  defaultCurrency?: string;
}

function InventoryRow({ item, onInventoryChanged, onNotify, defaultCurrency = "GHS" }: InventoryRowProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [isConfirmingDelete, setIsConfirmingDelete] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Form State
  const [quantity, setQuantity] = useState(item.quantity);
  const [unit, setUnit] = useState(item.unit || "");
  const [avgCost, setAvgCost] = useState<number | "">(item.avg_cost ?? "");
  const [threshold, setThreshold] = useState(item.low_stock_threshold);
  const [saleAmount, setSaleAmount] = useState<number | "">(item.sale_price_amount ?? "");
  const [saleQty, setSaleQty] = useState<number | "">(item.sale_price_quantity ?? "");

  // Keep state in sync if backend updates
  useEffect(() => {
    setQuantity(item.quantity);
    setUnit(item.unit || "");
    setAvgCost(item.avg_cost ?? "");
    setThreshold(item.low_stock_threshold);
    setSaleAmount(item.sale_price_amount ?? "");
    setSaleQty(item.sale_price_quantity ?? "");
  }, [item]);

  const isZero = item.quantity <= 0;
  const isLow = item.is_low_stock && !isZero;
  const itemLabel = formatItemLabel(item.item);
  const unitLabel = item.unit ? formatUnitLabel(item.unit, item.quantity) : null;
  const costUnitLabel = item.unit ? formatUnitLabel(item.unit, 1) : "unit";

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

  async function handleDelete() {
    setIsSaving(true);
    try {
      await deleteInventoryItem(item.item);
      onNotify?.("success", `${itemLabel} deleted from inventory.`);
      await onInventoryChanged?.();
    } catch (e) {
      onNotify?.("error", e instanceof Error ? e.message : "Could not delete item.");
    } finally {
      setIsSaving(false);
      setIsConfirmingDelete(false);
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setIsSaving(true);
    try {
      const payload: Partial<InventoryItem> = {
        quantity: quantity,
        unit: unit.trim(),
        avg_cost: avgCost === "" ? undefined : avgCost,
        low_stock_threshold: threshold,
        sale_price_amount: saleAmount === "" ? undefined : saleAmount,
        sale_price_quantity: saleQty === "" ? undefined : saleQty,
      };

      await updateInventoryItem(item.item, payload);
      onNotify?.("success", `${itemLabel} stock and settings updated.`);
      await onInventoryChanged?.();
      setIsEditing(false);
    } catch (e) {
      onNotify?.("error", e instanceof Error ? e.message : "Could not update inventory.");
    } finally {
      setIsSaving(false);
    }
  }

  if (isConfirmingDelete) {
    return (
      <div className="px-4 py-3 bg-red-50/50 border-y border-red-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-all duration-300">
        <div>
          <p className="text-sm font-semibold text-danger">
            Delete {itemLabel}?
          </p>
          <p className="text-2xs text-red-700">
            This removes the stock record and alert rules permanently. Ledger transactions are unchanged.
          </p>
        </div>
        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            disabled={isSaving}
            onClick={() => setIsConfirmingDelete(false)}
            className="px-3 py-1.5 rounded-lg border border-red-200 bg-white text-xs font-semibold text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isSaving}
            onClick={handleDelete}
            className="px-3 py-1.5 rounded-lg bg-danger text-white text-xs font-semibold hover:bg-red-700 disabled:opacity-50"
          >
            {isSaving ? "Deleting..." : "Yes, Delete"}
          </button>
        </div>
      </div>
    );
  }

  if (isEditing) {
    return (
      <form onSubmit={handleSave} className="p-4 bg-primary-surface/30 border-y border-primary-100 space-y-3 transition-all duration-300">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-primary-900 uppercase">
            Edit {itemLabel}
          </span>
          <span className="text-2xs text-text-secondary">
            Adjust stock levels and settings
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">Stock Quantity</span>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              min="0"
              step="0.0001"
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">Unit</span>
            <input
              type="text"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">Avg Cost (GHS)</span>
            <input
              type="number"
              value={avgCost}
              onChange={(e) => setAvgCost(e.target.value === "" ? "" : Number(e.target.value))}
              min="0"
              step="0.0001"
              placeholder="e.g. 15.00"
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">Alert Limit</span>
            <input
              type="number"
              value={threshold}
              onChange={(e) => setThreshold(Number(e.target.value))}
              min="0"
              step="0.1"
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">Selling Price</span>
            <input
              type="number"
              value={saleAmount}
              onChange={(e) => setSaleAmount(e.target.value === "" ? "" : Number(e.target.value))}
              min="0"
              step="0.0001"
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
          <label className="space-y-1">
            <span className="text-2xs font-semibold text-text-secondary uppercase">For Quantity</span>
            <input
              type="number"
              value={saleQty}
              onChange={(e) => setSaleQty(e.target.value === "" ? "" : Number(e.target.value))}
              min="0.0001"
              step="0.0001"
              className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary-light"
            />
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-1.5">
          <button
            type="button"
            disabled={isSaving}
            onClick={() => setIsEditing(false)}
            className="px-3 py-1.5 rounded-lg border border-border bg-white text-xs font-semibold text-text-secondary hover:bg-gray-50 disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSaving}
            className="px-3 py-1.5 rounded-lg bg-primary-900 text-white text-xs font-semibold hover:bg-primary-950 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    );
  }

  return (
    <div className="px-4 py-3 flex items-center justify-between gap-3 group hover:bg-primary-surface/10 transition-colors">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        {/* Status dot */}
        <div
          className={`h-2 w-2 rounded-full flex-shrink-0 ${
            isZero ? "bg-danger" : isLow ? "bg-warning" : "bg-primary-light"
          }`}
        />

        {/* Name + unit */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary truncate">
            {itemLabel}
          </p>
          {item.avg_cost != null && (
            <p className="text-2xs text-text-secondary">
              avg cost {formatAmount(item.avg_cost, defaultCurrency)} / {costUnitLabel}
            </p>
          )}
          {item.sale_price_amount != null && item.sale_price_quantity != null && (
            <p className="text-2xs text-primary-700">
              sells {formatAmount(item.sale_price_amount, item.sale_currency ?? defaultCurrency)} /{" "}
              {item.sale_price_quantity.toLocaleString()}{" "}
              {formatUnitLabel(item.unit ?? "unit", item.sale_price_quantity)}
            </p>
          )}
        </div>
      </div>

      {/* Right stock info + actions */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-right">
          <p
            className={`font-mono font-semibold text-sm ${
              isZero ? "text-danger" : isLow ? "text-warning" : "text-text-primary"
            }`}
          >
            {item.quantity.toLocaleString()}
            {unitLabel ? (
              <span className="font-sans font-normal text-text-secondary ml-1 text-xs">
                {unitLabel}
              </span>
            ) : null}
          </p>

          {/* Mini stock bar */}
          <div className="mt-1 h-1 w-16 bg-gray-100 rounded-full overflow-hidden ml-auto">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isZero ? "bg-danger" : isLow ? "bg-warning" : "bg-primary-light"
              }`}
              style={{ width: `${fillPct}%` }}
            />
          </div>
        </div>

        {/* Hover Action Buttons */}
        <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-200">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            title={`Edit ${itemLabel}`}
            className="h-8 w-8 rounded-full border border-border bg-white flex items-center justify-center text-text-secondary hover:border-primary-900 hover:text-primary-900 shadow-sm transition-colors"
          >
            <PencilIcon />
          </button>
          <button
            type="button"
            onClick={() => setIsConfirmingDelete(true)}
            title={`Delete ${itemLabel}`}
            className="h-8 w-8 rounded-full border border-border bg-white flex items-center justify-center text-text-secondary hover:border-danger hover:text-danger shadow-sm transition-colors"
          >
            <TrashIcon />
          </button>
        </div>
      </div>
    </div>
  );
}

// Keep the EmptyState and SkeletonList helpers as they were
function EmptyState() {
  return (
    <div className="px-4 py-8 text-center">
      <p className="text-4xl mb-2">📦</p>
      <p className="text-sm text-text-secondary">No inventory yet.</p>
      <p className="text-xs text-text-disabled mt-1">
        Add stock and a selling rule to start recording sales.
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
