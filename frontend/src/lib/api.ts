/**
 * Susu Books — API Client
 * Type-safe fetch wrapper for all FastAPI backend endpoints.
 * All requests go to localhost:8000 — no cloud, no CORS issues.
 */

import type {
  ChatResponse,
  ImageChatResponse,
  Transaction,
  InventoryItem,
  DailySummaryData,
  WeeklyReportData,
  InventoryAlerts,
} from "./types";

const BASE_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000")
    : "http://localhost:8000";

const DEFAULT_TIMEOUT_MS = 15_000;
const CHAT_TIMEOUT_MS = 180_000;

function buildUrl(path: string): string {
  return `${BASE_URL}${path}`;
}

function extractErrorDetail(body: unknown, fallback: string): string {
  if (!body || typeof body !== "object") return fallback;
  if ("detail" in body && typeof body.detail === "string") return body.detail;
  if ("error" in body && typeof body.error === "string") return body.error;
  return fallback;
}

async function parseErrorResponse(res: Response, path: string): Promise<never> {
  let detail = `HTTP ${res.status}`;
  try {
    const body = await res.json();
    detail = extractErrorDetail(body, detail);
  } catch {
    // ignore JSON parse errors
  }
  throw new ApiError(res.status, detail, path);
}

function withTimeout(timeoutMs: number): { controller: AbortController; cleanup: () => void } {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  return {
    controller,
    cleanup: () => clearTimeout(timeout),
  };
}

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers, ...rest } = options;
  const { controller, cleanup } = withTimeout(timeoutMs);

  try {
    const res = await fetch(buildUrl(path), {
      headers: {
        "Content-Type": "application/json",
        ...(headers as Record<string, string>),
      },
      signal: controller.signal,
      ...rest,
    });

    if (!res.ok) {
      return await parseErrorResponse(res, path);
    }

    return res.json() as Promise<T>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "The request took too long. Please try again.", path);
    }
    throw error;
  } finally {
    cleanup();
  }
}

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly path: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// AI / Chat
// ---------------------------------------------------------------------------

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export async function sendChat(
  message: string,
  language = "en",
  conversationHistory: ConversationMessage[] = []
): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, language, conversation_history: conversationHistory }),
    timeoutMs: CHAT_TIMEOUT_MS,
  });
}

export async function sendImageChat(
  imageFile: File,
  message = "What transactions can you see in this image?",
  language = "en"
): Promise<ImageChatResponse> {
  const form = new FormData();
  form.append("image", imageFile);
  form.append("message", message);
  form.append("language", language);

  const { controller, cleanup } = withTimeout(CHAT_TIMEOUT_MS);

  try {
    const res = await fetch(buildUrl("/api/chat/image"), {
      method: "POST",
      body: form,
      signal: controller.signal,
    });

    if (!res.ok) {
      return await parseErrorResponse(res, "/api/chat/image");
    }

    return res.json() as Promise<ImageChatResponse>;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "Image analysis took too long. Please try again.", "/api/chat/image");
    }
    throw error;
  } finally {
    cleanup();
  }
}

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

export async function getTransactions(params?: {
  date?: string;
  type?: "purchase" | "sale" | "expense";
  limit?: number;
  offset?: number;
}): Promise<Transaction[]> {
  const qs = new URLSearchParams();
  if (params?.date) qs.set("date", params.date);
  if (params?.type) qs.set("type", params.type);
  if (params?.limit != null) qs.set("limit", String(params.limit));
  if (params?.offset != null) qs.set("offset", String(params.offset));
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return request<Transaction[]>(`/api/transactions${query}`);
}

// ---------------------------------------------------------------------------
// Inventory
// ---------------------------------------------------------------------------

export async function getInventory(lowStockOnly = false): Promise<InventoryItem[]> {
  return request<InventoryItem[]>(
    `/api/inventory${lowStockOnly ? "?low_stock_only=true" : ""}`
  );
}

export async function getInventoryAlerts(): Promise<InventoryAlerts> {
  return request<InventoryAlerts>("/api/inventory/check/alerts");
}

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

export async function getDailySummary(date?: string): Promise<DailySummaryData> {
  const query = date ? `?date=${encodeURIComponent(date)}` : "";
  return request<DailySummaryData>(`/api/summary/daily${query}`);
}

export async function getWeeklyReport(): Promise<WeeklyReportData> {
  return request<WeeklyReportData>("/api/summary/weekly");
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthStatus {
  status: "ok" | "degraded";
  database: "ok" | "error";
  ollama_reachable: boolean;
  provider_reachable?: boolean;
  model_loaded: boolean;
  available_models?: string[];
  target_model: string;
  ai_provider?: "ollama";
  error?: string;
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health", { timeoutMs: 8_000 });
}

// ---------------------------------------------------------------------------
// Export / Backup
// ---------------------------------------------------------------------------

function getFilenameFromDisposition(contentDisposition: string | null, fallback: string): string {
  if (!contentDisposition) return fallback;
  const match = /filename="?([^"]+)"?/.exec(contentDisposition);
  return match?.[1] ?? fallback;
}

async function downloadFile(
  path: string,
  fallbackFilename: string,
  options: RequestInit & { timeoutMs?: number } = {}
): Promise<string> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...rest } = options;
  const { controller, cleanup } = withTimeout(timeoutMs);

  try {
    const res = await fetch(buildUrl(path), {
      signal: controller.signal,
      ...rest,
    });
    if (!res.ok) {
      return await parseErrorResponse(res, path);
    }

    const blob = await res.blob();
    const filename = getFilenameFromDisposition(
      res.headers.get("Content-Disposition"),
      fallbackFilename
    );
    const objectUrl = window.URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = objectUrl;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(objectUrl);
    return filename;
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError(408, "The export took too long. Please try again.", path);
    }
    throw error;
  } finally {
    cleanup();
  }
}

export async function downloadTransactionsCsv(): Promise<string> {
  return downloadFile(
    "/api/export/transactions.csv",
    "susu-books-transactions.csv",
    { timeoutMs: 30_000 }
  );
}

export async function downloadBackupJson(includeAuditTrail = false): Promise<string> {
  return downloadFile(
    `/api/export/backup.json?include_audit_trail=${includeAuditTrail ? "true" : "false"}`,
    "susu-books-backup.json",
    { timeoutMs: 30_000 }
  );
}
