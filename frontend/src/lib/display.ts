import type { Transaction } from "./types";

const EXPENSE_CATEGORY_LABELS: Record<string, string> = {
  market_fee: "Market stall fee",
  transport: "Transport",
  utilities: "Utilities",
  rent: "Rent",
  staff: "Staff wages",
  phone: "Phone credit",
  food: "Food",
  other: "Other expense",
};

const ITEM_LABELS: Record<string, string> = {
  palm_oil: "Palm oil",
};

export function formatItemLabel(item: string): string {
  return titleCase(humanizeToken(item));
}

export function formatTransactionTitle(transaction: Transaction): string {
  if (transaction.type === "expense") {
    return sentenceCase(humanizeToken(transaction.item));
  }

  return formatItemLabel(transaction.item);
}

export function formatTransactionSubtitle(transaction: Transaction): string | null {
  if (transaction.counterparty) {
    return titleCase(humanizeToken(transaction.counterparty));
  }

  if (transaction.category) {
    return EXPENSE_CATEGORY_LABELS[transaction.category] ?? titleCase(humanizeToken(transaction.category));
  }

  return null;
}

export function formatUnitLabel(unit: string, quantity?: number): string {
  const clean = humanizeToken(unit).toLowerCase();
  if (quantity == null) return clean;

  if (quantity === 1) {
    return singularize(clean);
  }

  return pluralize(clean);
}

export function titleCase(value: string): string {
  return value.replace(/\b\w/g, (char) => char.toUpperCase());
}

export function sentenceCase(value: string): string {
  if (!value) return value;
  return value[0].toUpperCase() + value.slice(1);
}

function humanizeToken(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;

  const mapped = ITEM_LABELS[trimmed.toLowerCase()];
  if (mapped) return mapped;

  return trimmed
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function singularize(value: string): string {
  if (value.endsWith("ies")) return value.slice(0, -3) + "y";
  if (value.endsWith("s") && !value.endsWith("ss")) return value.slice(0, -1);
  return value;
}

function pluralize(value: string): string {
  if (value.endsWith("s")) return value;
  if (value.endsWith("y") && !/[aeiou]y$/.test(value)) return value.slice(0, -1) + "ies";
  return value + "s";
}
