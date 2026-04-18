"use client";
/**
 * Susu Books — useApi hook
 * Central data management hook for all backend API calls.
 * Handles loading states, error recovery, and periodic refresh.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "@/lib/api";
import type {
  Transaction,
  InventoryItem,
  DailySummaryData,
  WeeklyReportData,
  InventoryAlerts,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiState {
  transactions: Transaction[];
  inventory: InventoryItem[];
  dailySummary: DailySummaryData | null;
  weeklyReport: WeeklyReportData | null;
  inventoryAlerts: InventoryAlerts | null;
  backendOnline: boolean;
  isLoadingInitial: boolean;
  errors: Record<string, string>;
}

export interface UseApiReturn extends ApiState {
  /** Refresh all data from the backend */
  refreshAll: () => Promise<void>;
  /** Refresh only today's transactions and summary */
  refreshToday: () => Promise<void>;
  /** Prepend transactions (received from an AI chat response) into the feed */
  ingestTransactions: (txns: Transaction[]) => void;
  /** Clear a specific error key */
  clearError: (key: string) => void;
}

// Polling interval in milliseconds (30 seconds)
const POLL_INTERVAL_MS = 30_000;

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useApi(): UseApiReturn {
  const [state, setState] = useState<ApiState>({
    transactions: [],
    inventory: [],
    dailySummary: null,
    weeklyReport: null,
    inventoryAlerts: null,
    backendOnline: false,
    isLoadingInitial: true,
    errors: {},
  });

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  // Safe setState that only runs if still mounted
  const safeSet = useCallback(
    (updater: (prev: ApiState) => ApiState) => {
      if (mountedRef.current) setState(updater);
    },
    []
  );

  const setError = useCallback(
    (key: string, message: string) => {
      safeSet((prev) => ({
        ...prev,
        errors: { ...prev.errors, [key]: message },
      }));
    },
    [safeSet]
  );

  const clearError = useCallback(
    (key: string) => {
      safeSet((prev) => {
        const errors = { ...prev.errors };
        delete errors[key];
        return { ...prev, errors };
      });
    },
    [safeSet]
  );

  // ---------------------------------------------------------------------------
  // Individual fetchers (non-throwing — errors stored in state)
  // ---------------------------------------------------------------------------

  const fetchTransactions = useCallback(async () => {
    try {
      const txns = await api.getTransactions({ limit: 100 });
      safeSet((prev) => {
        const errors = { ...prev.errors };
        delete errors.transactions;
        return { ...prev, transactions: txns, errors };
      });
    } catch (e) {
      setError("transactions", String(e));
    }
  }, [safeSet, setError]);

  const fetchInventory = useCallback(async () => {
    try {
      const [inv, alerts] = await Promise.all([
        api.getInventory(),
        api.getInventoryAlerts(),
      ]);
      safeSet((prev) => {
        const errors = { ...prev.errors };
        delete errors.inventory;
        return { ...prev, inventory: inv, inventoryAlerts: alerts, errors };
      });
    } catch (e) {
      setError("inventory", String(e));
    }
  }, [safeSet, setError]);

  const fetchDailySummary = useCallback(async () => {
    try {
      const summary = await api.getDailySummary();
      safeSet((prev) => {
        const errors = { ...prev.errors };
        delete errors.dailySummary;
        return { ...prev, dailySummary: summary, errors };
      });
    } catch (e) {
      setError("dailySummary", String(e));
    }
  }, [safeSet, setError]);

  const fetchWeeklyReport = useCallback(async () => {
    try {
      const report = await api.getWeeklyReport();
      safeSet((prev) => {
        const errors = { ...prev.errors };
        delete errors.weeklyReport;
        return { ...prev, weeklyReport: report, errors };
      });
    } catch (e) {
      setError("weeklyReport", String(e));
    }
  }, [safeSet, setError]);

  const checkHealth = useCallback(async () => {
    try {
      const health = await api.getHealth();
      safeSet((prev) => ({
        ...prev,
        backendOnline: health.status !== "degraded",
      }));
    } catch {
      safeSet((prev) => ({ ...prev, backendOnline: false }));
    }
  }, [safeSet]);

  // ---------------------------------------------------------------------------
  // Composite refresh methods
  // ---------------------------------------------------------------------------

  const refreshToday = useCallback(async () => {
    await Promise.allSettled([fetchTransactions(), fetchDailySummary(), fetchInventory()]);
  }, [fetchTransactions, fetchDailySummary, fetchInventory]);

  const refreshAll = useCallback(async () => {
    safeSet((prev) => ({ ...prev, errors: {} }));
    await Promise.allSettled([
      checkHealth(),
      fetchTransactions(),
      fetchInventory(),
      fetchDailySummary(),
      fetchWeeklyReport(),
    ]);
    safeSet((prev) => ({ ...prev, isLoadingInitial: false }));
  }, [
    checkHealth,
    fetchTransactions,
    fetchInventory,
    fetchDailySummary,
    fetchWeeklyReport,
    safeSet,
  ]);

  // ---------------------------------------------------------------------------
  // Ingest transactions from chat responses (add to front of feed)
  // ---------------------------------------------------------------------------

  const ingestTransactions = useCallback(
    (newTxns: Transaction[]) => {
      if (!newTxns.length) return;
      safeSet((prev) => {
        // Deduplicate by id
        const existingIds = new Set(prev.transactions.map((t) => t.id));
        const fresh = newTxns.filter((t) => !existingIds.has(t.id));
        return {
          ...prev,
          transactions: [...fresh, ...prev.transactions].slice(0, 200),
        };
      });
      // Refresh summary after a brief delay (backend needs to commit first)
      window.setTimeout(() => {
        fetchDailySummary();
        fetchInventory();
      }, 500);
    },
    [safeSet, fetchDailySummary, fetchInventory]
  );

  // ---------------------------------------------------------------------------
  // Lifecycle: initial load + polling
  // ---------------------------------------------------------------------------

  useEffect(() => {
    mountedRef.current = true;

    // Initial load
    refreshAll();

    // Refresh weekly data less frequently (every 5 minutes)
    const weeklyTimer = setInterval(fetchWeeklyReport, 5 * 60_000);

    // Poll today's data every 30 seconds
    pollingRef.current = setInterval(refreshToday, POLL_INTERVAL_MS);

    return () => {
      mountedRef.current = false;
      if (pollingRef.current) clearInterval(pollingRef.current);
      clearInterval(weeklyTimer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    ...state,
    refreshAll,
    refreshToday,
    ingestTransactions,
    clearError,
  };
}
