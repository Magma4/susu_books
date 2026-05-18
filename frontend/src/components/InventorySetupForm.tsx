"use client";

import { useState, type FormEvent } from "react";

import { setupInventoryItem } from "@/lib/api";
import type { InventorySetupPayload } from "@/lib/types";

interface InventorySetupFormProps {
  collapsible?: boolean;
  initialOpen?: boolean;
  onInventoryChanged?: () => Promise<void> | void;
  onNotify?: (type: "success" | "error", message: string) => void;
  onSaved?: () => void;
}

const DEFAULT_FORM: InventorySetupPayload = {
  item: "plantains",
  quantity: 40,
  unit: "pieces",
  sale_price_amount: 8,
  sale_price_quantity: 4,
  sale_currency: "GHS",
  low_stock_threshold: 5,
};

export default function InventorySetupForm({
  collapsible = true,
  initialOpen = false,
  onInventoryChanged,
  onNotify,
  onSaved,
}: InventorySetupFormProps) {
  const [isOpen, setIsOpen] = useState(initialOpen || !collapsible);
  const [isSaving, setIsSaving] = useState(false);
  const [form, setForm] = useState<InventorySetupPayload>(DEFAULT_FORM);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const payload: InventorySetupPayload = {
      ...form,
      item: form.item.trim(),
      unit: form.unit.trim() || "pieces",
      sale_currency: (form.sale_currency || "GHS").trim().toUpperCase(),
    };

    if (!payload.item) {
      onNotify?.("error", "Add the item name first.");
      return;
    }

    if (
      payload.quantity < 0 ||
      payload.sale_price_amount <= 0 ||
      payload.sale_price_quantity <= 0
    ) {
      onNotify?.("error", "Stock and selling price need valid numbers.");
      return;
    }

    setIsSaving(true);
    try {
      await setupInventoryItem(payload);
      await onInventoryChanged?.();
      onNotify?.("success", `${payload.item} stock and selling rule saved.`);
      if (collapsible) setIsOpen(false);
      onSaved?.();
    } catch (error) {
      onNotify?.(
        "error",
        error instanceof Error ? error.message : "Could not save inventory."
      );
    } finally {
      setIsSaving(false);
    }
  }

  const setValue = (key: keyof InventorySetupPayload, value: string) => {
    setForm((prev) => {
      if (key === "avg_cost" || key === "low_stock_threshold") {
        return {
          ...prev,
          [key]: value.trim() === "" ? undefined : Number(value),
        };
      }

      if (
        key === "quantity" ||
        key === "sale_price_amount" ||
        key === "sale_price_quantity"
      ) {
        return {
          ...prev,
          [key]: value.trim() === "" ? 0 : Number(value),
        };
      }

      return { ...prev, [key]: value };
    });
  };

  return (
    <div
      className={
        collapsible
          ? "border-b border-border bg-primary-surface/30 px-4 py-3"
          : "bg-white"
      }
    >
      {collapsible ? (
        <button
          type="button"
          onClick={() => setIsOpen((v) => !v)}
          className="w-full flex items-center justify-between text-left"
        >
          <span>
            <span className="block text-xs font-semibold text-primary-900 uppercase tracking-wide">
              Add inventory
            </span>
            <span className="block text-2xs text-text-secondary">
              Set stock and selling price, then speak only sales.
            </span>
          </span>
          <span className="text-primary-900 font-semibold">
            {isOpen ? "Close" : "Set up"}
          </span>
        </button>
      ) : (
        <div className="mb-4 rounded-2xl bg-primary-surface/70 border border-primary-100 px-4 py-3">
          <p className="text-xs font-semibold text-primary-900 uppercase tracking-wide">
            Stock setup
          </p>
          <p className="mt-1 text-xs text-text-secondary">
            Example: plantains, 40 pieces, GHS 8 for 4 pieces. After this, a
            sale like &quot;borode 8 cedis&quot; can subtract the right quantity.
          </p>
        </div>
      )}

      {isOpen && (
        <form
          onSubmit={handleSubmit}
          className={
            collapsible
              ? "mt-3 grid grid-cols-2 gap-2 text-xs"
              : "grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm"
          }
        >
          <Input label="Item" value={form.item} onChange={(v) => setValue("item", v)} />
          <Input
            label="Current stock"
            type="number"
            value={form.quantity}
            onChange={(v) => setValue("quantity", v)}
          />
          <Input label="Unit" value={form.unit} onChange={(v) => setValue("unit", v)} />
          <Input
            label="Selling price"
            type="number"
            value={form.sale_price_amount}
            onChange={(v) => setValue("sale_price_amount", v)}
          />
          <Input
            label="For quantity"
            type="number"
            value={form.sale_price_quantity}
            onChange={(v) => setValue("sale_price_quantity", v)}
          />
          <Input
            label="Currency"
            value={form.sale_currency ?? "GHS"}
            onChange={(v) => setValue("sale_currency", v)}
          />
          <Input
            label="Cost per unit"
            type="number"
            value={form.avg_cost ?? ""}
            onChange={(v) => setValue("avg_cost", v)}
          />
          <Input
            label="Low stock alert"
            type="number"
            value={form.low_stock_threshold ?? ""}
            onChange={(v) => setValue("low_stock_threshold", v)}
          />
          <button
            type="submit"
            disabled={isSaving}
            className="col-span-1 sm:col-span-2 rounded-xl bg-primary-900 text-white font-semibold py-3 disabled:opacity-50"
          >
            {isSaving ? "Saving..." : "Save inventory"}
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
      <span className="text-2xs font-semibold text-text-secondary uppercase">
        {label}
      </span>
      <input
        type={type}
        value={value}
        min={type === "number" ? "0" : undefined}
        step={type === "number" ? "0.01" : undefined}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-lg border border-border bg-white px-3 py-2 text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-light"
      />
    </label>
  );
}
