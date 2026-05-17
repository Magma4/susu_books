"use client";
/**
 * InventoryPanel — Grid of current inventory items with stock level indicators.
 * Highlights low-stock and zero-stock items with amber/red badges.
 */

import { useState, type FormEvent } from "react";
import { setupInventoryItem } from "@/lib/api";
import type { InventoryItem, InventorySetupPayload } from "@/lib/types";
import { formatItemLabel, formatUnitLabel } from "@/lib/display";
import { formatAmount } from "@/styles/theme";

interface InventoryPanelProps {
  items: InventoryItem[];
  isLoading?: boolean;
  onInventoryChanged?: () => Promise<void> | void;
  onNotify?: (type: "success" | "error", message: string) => void;
}

export default function InventoryPanel({
  items,
  isLoading = false,
  onInventoryChanged,
  onNotify,
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
        <p className="text-sm font-medium text-text-primary truncate">
          {itemLabel}
        </p>
        {item.avg_cost != null && (
          <p className="text-2xs text-text-secondary">
            avg cost {formatAmount(item.avg_cost, "GHS")} / {costUnitLabel}
          </p>
        )}
        {item.sale_price_amount != null && item.sale_price_quantity != null && (
          <p className="text-2xs text-primary-700">
            sells {formatAmount(item.sale_price_amount, item.sale_currency ?? "GHS")} /{" "}
            {item.sale_price_quantity.toLocaleString()}{" "}
            {formatUnitLabel(item.unit ?? "unit", item.sale_price_quantity)}
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
          {unitLabel ? (
            <span className="font-sans font-normal text-text-secondary ml-1 text-xs">
              {unitLabel}
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

function InventorySetupForm({
  onInventoryChanged,
  onNotify,
}: {
  onInventoryChanged?: () => Promise<void> | void;
  onNotify?: (type: "success" | "error", message: string) => void;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<InventorySetupPayload>({
    item: "plantains",
    quantity: 40,
    unit: "pieces",
    sale_price_amount: 8,
    sale_price_quantity: 4,
    sale_currency: "GHS",
    low_stock_threshold: 5,
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    try {
      await setupInventoryItem(form);
      await onInventoryChanged?.();
      onNotify?.("success", `${form.item} stock and selling rule saved.`);
      setIsOpen(false);
    } catch (error) {
      onNotify?.("error", error instanceof Error ? error.message : "Could not save inventory.");
    } finally {
      setIsSaving(false);
    }
  }

  const setValue = (key: keyof InventorySetupPayload, value: string) => {
    setForm((prev) => ({
      ...prev,
      [key]: ["quantity", "sale_price_amount", "sale_price_quantity", "avg_cost", "low_stock_threshold"].includes(key)
        ? Number(value)
        : value,
    }));
  };

  return (
    <div className="border-b border-border bg-primary-surface/30 px-4 py-3">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center justify-between text-left"
      >
        <span>
          <span className="block text-xs font-semibold text-primary-900 uppercase tracking-wide">
            Add stock and price
          </span>
          <span className="block text-2xs text-text-secondary">
            Example: 8 cedis per 4 plantains, then speak only sales.
          </span>
        </span>
        <span className="text-primary-900 font-semibold">{isOpen ? "Close" : "Set up"}</span>
      </button>

      {isOpen && (
        <form onSubmit={handleSubmit} className="mt-3 grid grid-cols-2 gap-2 text-xs">
          <Input label="Item" value={form.item} onChange={(v) => setValue("item", v)} />
          <Input label="Stock" type="number" value={form.quantity} onChange={(v) => setValue("quantity", v)} />
          <Input label="Unit" value={form.unit} onChange={(v) => setValue("unit", v)} />
          <Input label="Price" type="number" value={form.sale_price_amount} onChange={(v) => setValue("sale_price_amount", v)} />
          <Input label="For quantity" type="number" value={form.sale_price_quantity} onChange={(v) => setValue("sale_price_quantity", v)} />
          <Input label="Low stock" type="number" value={form.low_stock_threshold ?? 5} onChange={(v) => setValue("low_stock_threshold", v)} />
          <button
            type="submit"
            disabled={isSaving}
            className="col-span-2 rounded-xl bg-primary-900 text-white font-semibold py-2 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save inventory rule"}
          </button>
        </form>
      )}
    </div>
  );
}

function Input({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="space-y-1">
      <span className="text-2xs font-semibold text-text-secondary uppercase">{label}</span>
      <input
        type={type}
        value={value}
        min={type === "number" ? "0" : undefined}
        step={type === "number" ? "0.01" : undefined}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-border bg-white px-2 py-1.5 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-light"
      />
    </label>
  );
}

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
