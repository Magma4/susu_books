"use client";
/**
 * TransactionFeed — Scrollable live ledger of today's transactions.
 * Features elegant hover controls for inline transaction editing and deletion.
 */

import { useEffect, useRef, useState } from "react";
import TransactionCard from "./TransactionCard";
import type { Transaction } from "@/lib/types";
import { deleteTransaction, updateTransaction } from "@/lib/api";

interface TransactionFeedProps {
  transactions: Transaction[];
  isLoading?: boolean;
  onTransactionChanged?: () => void;
  onNotify?: (type: "success" | "error" | "info" | "warning", msg: string) => void;
  filterDate?: string;
  onFilterDateChange?: (date: string) => void;
}

export default function TransactionFeed({
  transactions,
  isLoading = false,
  onTransactionChanged,
  onNotify,
  filterDate = "",
  onFilterDateChange,
}: TransactionFeedProps) {
  const [newIds, setNewIds] = useState<Set<number>>(new Set());
  const prevCountRef = useRef(transactions.length);
  const containerRef = useRef<HTMLDivElement>(null);

  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [deletingTransaction, setDeletingTransaction] = useState<Transaction | null>(null);

  useEffect(() => {
    const prev = prevCountRef.current;
    const curr = transactions.length;
    if (curr > prev) {
      const freshIds = transactions.slice(0, curr - prev).map((t) => t.id);
      setNewIds(new Set(freshIds));
      const timer = setTimeout(() => setNewIds(new Set()), 600);
      return () => clearTimeout(timer);
    }
    prevCountRef.current = curr;
  }, [transactions]);

  const filteredTransactions = transactions.filter((t) => {
    if (!filterDate) return true;
    const tDate = t.created_at.split("T")[0];
    return tDate === filterDate;
  });

  const todayLabel = new Date().toLocaleDateString("en-GH", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });

  const salesCount = filteredTransactions.filter((t) => t.type === "sale").length;
  const purchasesCount = filteredTransactions.filter((t) => t.type === "purchase").length;
  const expensesCount = filteredTransactions.filter((t) => t.type === "expense").length;

  const handleSaveEdit = async (id: number, payload: Partial<Transaction>) => {
    try {
      await updateTransaction(id, payload);
      onNotify?.("success", "Transaction updated and stock levels re-synced!");
      onTransactionChanged?.();
      setEditingTransaction(null);
    } catch (err) {
      onNotify?.("error", err instanceof Error ? err.message : "Failed to update transaction.");
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deletingTransaction) return;
    try {
      await deleteTransaction(deletingTransaction.id);
      onNotify?.("success", "Transaction deleted and inventory restored!");
      onTransactionChanged?.();
      setDeletingTransaction(null);
    } catch (err) {
      onNotify?.("error", err instanceof Error ? err.message : "Failed to delete transaction.");
    }
  };

  // Format active date label
  const activeDateLabel = filterDate
    ? new Date(filterDate).toLocaleDateString("en-GH", {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "All Dates";

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border flex-shrink-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
              {filterDate ? "Filtered Ledger" : "All Transactions"}
            </span>
            <p className="text-xs text-text-disabled mt-0.5">{activeDateLabel}</p>
          </div>

          <div className="flex items-center gap-2">
            {/* Native Date Picker */}
            <label htmlFor="ledger-date-filter" className="sr-only">Filter by Date</label>
            <input
              id="ledger-date-filter"
              type="date"
              value={filterDate}
              onChange={(e) => onFilterDateChange?.(e.target.value)}
              className="text-xs border border-border rounded-xl px-2.5 py-1.5 bg-background text-text-secondary focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent cursor-pointer"
            />
            {filterDate && (
              <button
                type="button"
                onClick={() => onFilterDateChange?.("")}
                className="text-xs font-medium text-primary-900 hover:text-primary-700 bg-primary-surface px-2.5 py-1.5 rounded-xl active:scale-95 transition-all"
              >
                Clear
              </button>
            )}
          </div>
        </div>

        {/* Type summary pills */}
        {filteredTransactions.length > 0 && (
          <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-border/50">
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

      {/* Transaction list */}
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto overscroll-contain"
        style={{ minHeight: "300px", maxHeight: "calc(100vh - 320px)" }}
      >
        {isLoading ? (
          <SkeletonList />
        ) : filteredTransactions.length === 0 ? (
          filterDate ? (
            <div className="flex flex-col items-center justify-center h-48 px-6 text-center">
              <div className="text-4xl mb-3">📅</div>
              <p className="text-sm font-semibold text-text-secondary">
                No transactions found
              </p>
              <p className="text-xs text-text-disabled mt-1">
                No records exist on {activeDateLabel}
              </p>
            </div>
          ) : (
            <EmptyState />
          )
        ) : (
          <div className="p-3 space-y-2">
            {filteredTransactions.map((tx) => (
              <TransactionCard
                key={tx.id}
                transaction={tx}
                isNew={newIds.has(tx.id)}
                onEdit={setEditingTransaction}
                onDelete={setDeletingTransaction}
              />
            ))}
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editingTransaction && (
        <EditModal
          transaction={editingTransaction}
          onClose={() => setEditingTransaction(null)}
          onSave={handleSaveEdit}
        />
      )}

      {/* Delete modal */}
      {deletingTransaction && (
        <DeleteModal
          transaction={deletingTransaction}
          onClose={() => setDeletingTransaction(null)}
          onConfirm={handleDeleteConfirm}
        />
      )}
    </div>
  );
}

// Modals

function EditModal({
  transaction: tx,
  onClose,
  onSave,
}: {
  transaction: Transaction;
  onClose: () => void;
  onSave: (id: number, payload: Partial<Transaction>) => Promise<void>;
}) {
  const [item, setItem] = useState(tx.item || "");
  const [type, setType] = useState(tx.type);
  const [quantity, setQuantity] = useState<number | "">(tx.quantity ?? "");
  const [unit, setUnit] = useState(tx.unit || "");
  const [unitPrice, setUnitPrice] = useState<number | "">(tx.unit_price ?? "");
  const [totalAmount, setTotalAmount] = useState<number | "">(tx.total_amount);
  const [counterparty, setCounterparty] = useState(tx.counterparty || "");
  const [notes, setNotes] = useState(tx.notes || "");
  const [isSaving, setIsSaving] = useState(false);

  // Auto calculate total amount on price/quantity updates
  useEffect(() => {
    if (quantity !== "" && unitPrice !== "") {
      setTotalAmount(Number(quantity) * Number(unitPrice));
    }
  }, [quantity, unitPrice]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!item.trim() && type !== "expense") return;
    setIsSaving(true);
    try {
      const payload: Partial<Transaction> = {
        item: type === "expense" ? tx.item : item.trim(),
        type,
        quantity: quantity === "" ? undefined : Number(quantity),
        unit: unit.trim() || undefined,
        unit_price: unitPrice === "" ? undefined : Number(unitPrice),
        total_amount: Number(totalAmount),
        counterparty: counterparty.trim() || undefined,
        notes: notes.trim() || undefined,
      };
      await onSave(tx.id, payload);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm px-4 py-6 flex items-end sm:items-center justify-center animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full max-w-md mx-auto shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="px-5 py-4 border-b border-border flex items-center justify-between">
          <h3 className="text-base font-bold text-text-primary">
            Edit Transaction
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-text-disabled hover:text-text-secondary p-1"
            aria-label="Close modal"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 overflow-y-auto flex-1">
          {/* Item Name */}
          {type !== "expense" && (
            <div>
              <label htmlFor="edit-item-name" className="block text-xs font-semibold text-text-secondary mb-1.5">
                Item Name *
              </label>
              <input
                id="edit-item-name"
                type="text"
                required
                value={item}
                onChange={(e) => setItem(e.target.value)}
                placeholder="e.g. Tomatoes"
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
              />
            </div>
          )}

          {/* Type dropdown */}
          <div>
            <label htmlFor="edit-type" className="block text-xs font-semibold text-text-secondary mb-1.5">
              Transaction Type
            </label>
            <select
              id="edit-type"
              value={type}
              onChange={(e) => setType(e.target.value as "sale" | "purchase" | "expense")}
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
            >
              <option value="sale">Sale (Income)</option>
              <option value="purchase">Purchase (Stock In)</option>
              <option value="expense">Expense (Cost)</option>
            </select>
          </div>

          {/* Quantity & Unit Row */}
          {type !== "expense" && (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="edit-qty" className="block text-xs font-semibold text-text-secondary mb-1.5">
                  Quantity
                </label>
                <input
                  id="edit-qty"
                  type="number"
                  step="any"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="e.g. 5"
                  className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                />
              </div>
              <div>
                <label htmlFor="edit-unit" className="block text-xs font-semibold text-text-secondary mb-1.5">
                  Unit
                </label>
                <input
                  id="edit-unit"
                  type="text"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  placeholder="e.g. bags"
                  className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                />
              </div>
            </div>
          )}

          {/* Price & Total Amount Row */}
          <div className="grid grid-cols-2 gap-3">
            {type !== "expense" ? (
              <div>
                <label htmlFor="edit-price" className="block text-xs font-semibold text-text-secondary mb-1.5">
                  Unit Price (GHS)
                </label>
                <input
                  id="edit-price"
                  type="number"
                  step="any"
                  value={unitPrice}
                  onChange={(e) => setUnitPrice(e.target.value === "" ? "" : Number(e.target.value))}
                  placeholder="e.g. 15"
                  className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                />
              </div>
            ) : (
              <div className="col-span-2">
                <label htmlFor="edit-category-name" className="block text-xs font-semibold text-text-secondary mb-1.5">
                  Category / Description
                </label>
                <input
                  id="edit-category-name"
                  type="text"
                  required
                  value={item}
                  onChange={(e) => setItem(e.target.value)}
                  placeholder="e.g. Stall rent"
                  className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
                />
              </div>
            )}
            <div className={type === "expense" ? "col-span-2" : ""}>
              <label htmlFor="edit-total" className="block text-xs font-semibold text-text-secondary mb-1.5">
                Total Amount (GHS)
              </label>
              <input
                id="edit-total"
                type="number"
                step="any"
                required
                value={totalAmount}
                onChange={(e) => setTotalAmount(e.target.value === "" ? "" : Number(e.target.value))}
                placeholder="e.g. 75"
                className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
              />
            </div>
          </div>

          {/* Counterparty */}
          <div>
            <label htmlFor="edit-counterparty" className="block text-xs font-semibold text-text-secondary mb-1.5">
              {type === "sale" ? "Customer Name" : type === "purchase" ? "Supplier Name" : "Paid To"}
            </label>
            <input
              id="edit-counterparty"
              type="text"
              value={counterparty}
              onChange={(e) => setCounterparty(e.target.value)}
              placeholder="e.g. Kojo"
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent"
            />
          </div>

          {/* Notes */}
          <div>
            <label htmlFor="edit-notes" className="block text-xs font-semibold text-text-secondary mb-1.5">
              Notes
            </label>
            <textarea
              id="edit-notes"
              rows={2}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any extra details..."
              className="w-full rounded-xl border border-border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent resize-none"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={isSaving}
              className="flex-1 py-2.5 rounded-xl border-2 border-border text-sm font-semibold text-text-secondary hover:border-text-secondary transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSaving}
              className="flex-1 py-2.5 rounded-xl bg-primary-900 text-white text-sm font-semibold hover:bg-primary-700 active:scale-95 transition-all flex items-center justify-center gap-2"
            >
              {isSaving ? (
                <>
                  <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                  Saving…
                </>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function DeleteModal({
  transaction: tx,
  onClose,
  onConfirm,
}: {
  transaction: Transaction;
  onClose: () => void;
  onConfirm: () => Promise<void>;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    setIsDeleting(true);
    try {
      await onConfirm();
    } finally {
      setIsDeleting(false);
    }
  };

  const desc = tx.quantity
    ? `${tx.quantity} ${tx.unit || ""} of ${tx.item || tx.category || "item"}`
    : tx.item || tx.category || "item";

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm px-4 py-6 flex items-end sm:items-center justify-center animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div className="bg-white rounded-t-3xl sm:rounded-2xl w-full max-w-sm mx-auto shadow-2xl overflow-hidden p-5">
        <div className="text-center">
          <div className="h-12 w-12 rounded-full bg-red-50 text-danger flex items-center justify-center mx-auto mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-base font-bold text-text-primary mb-1">
            Delete Transaction?
          </h3>
          <p className="text-xs text-text-secondary leading-relaxed mb-4">
            Are you sure you want to delete this {tx.type}:
            <br />
            <strong className="text-text-primary font-semibold">{desc}</strong>?
            {tx.type !== "expense" && (
              <>
                <br />
                <span className="text-danger font-medium mt-1 block">
                  ⚠️ This will automatically restore or deduct stock from your active inventory.
                </span>
              </>
            )}
          </p>
        </div>

        <div className="flex gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isDeleting}
            className="flex-1 py-2.5 rounded-xl border-2 border-border text-sm font-semibold text-text-secondary hover:border-text-secondary transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={isDeleting}
            className="flex-1 py-2.5 rounded-xl bg-danger text-white text-sm font-semibold hover:bg-red-700 active:scale-95 transition-all flex items-center justify-center gap-2"
          >
            {isDeleting ? (
              <>
                <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                Deleting…
              </>
            ) : (
              "Delete"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

// Helpers

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
