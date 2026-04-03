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

// ---------------------------------------------------------------------------
// Core fetch helper
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    },
    ...options,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore JSON parse error
    }
    throw new ApiError(res.status, detail, path);
  }

  return res.json() as Promise<T>;
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

  const url = `${BASE_URL}/api/chat/image`;
  const res = await fetch(url, { method: "POST", body: form });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      // ignore
    }
    throw new ApiError(res.status, detail, "/api/chat/image");
  }

  return res.json() as Promise<ImageChatResponse>;
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
  model_loaded: boolean;
  available_models?: string[];
  target_model: string;
  error?: string;
}

export async function getHealth(): Promise<HealthStatus> {
  return request<HealthStatus>("/api/health");
}
