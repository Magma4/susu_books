// Susu Books — shared TypeScript types matching the FastAPI backend schemas

// ---------------------------------------------------------------------------
// Core domain types
// ---------------------------------------------------------------------------

export type TransactionType = "purchase" | "sale" | "expense";
export type TransactionSource = "voice" | "photo" | "manual";

export interface Transaction {
  id: number;
  type: TransactionType;
  item: string;
  quantity?: number;
  unit?: string;
  unit_price?: number;
  total_amount: number;
  currency: string;
  counterparty?: string;
  category?: string;
  notes?: string;
  source: TransactionSource;
  language: string;
  raw_input?: string;
  confidence: number;
  created_at: string; // ISO datetime string
  updated_at: string;
}

export interface InventoryItem {
  id: number;
  item: string;
  quantity: number;
  unit?: string;
  avg_cost?: number;
  last_purchase_price?: number;
  last_sale_price?: number;
  low_stock_threshold: number;
  is_low_stock: boolean;
  created_at?: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Report types
// ---------------------------------------------------------------------------

export interface ComparisonToYesterday {
  yesterday_revenue: number;
  yesterday_profit: number;
  revenue_change: number;
  profit_change: number;
  revenue_change_pct?: number;
}

export interface DailySummaryData {
  date: string;
  total_revenue: number;
  total_cost: number;
  total_expenses: number;
  net_profit: number;
  transaction_count: number;
  top_selling_item?: string;
  profit_margin_pct?: number;
  comparison_to_yesterday?: ComparisonToYesterday;
}

export interface DayData {
  date: string;
  revenue: number;
  cost: number;
  expenses: number;
  profit: number;
  transaction_count: number;
}

export interface TopItem {
  item: string;
  revenue: number;
}

export interface WeeklyReportData {
  start_date: string;
  end_date: string;
  total_revenue: number;
  total_cost: number;
  total_expenses: number;
  total_profit: number;
  avg_daily_profit: number;
  best_day?: DayData;
  worst_day?: DayData;
  daily_trend: DayData[];
  top_items_by_revenue: TopItem[];
}

export interface InventoryAlerts {
  total_items: number;
  low_stock_count: number;
  zero_stock_count: number;
  low_stock_items: { item: string; quantity: number; unit?: string; threshold: number }[];
  zero_stock_items: { item: string; unit?: string }[];
}

// ---------------------------------------------------------------------------
// AI / Chat types
// ---------------------------------------------------------------------------

export interface FunctionCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  result?: Record<string, unknown>;
  success: boolean;
  error?: string;
}

export interface ChatResponse {
  response: string;
  transactions: Transaction[];
  function_calls: FunctionCallRecord[];
  language?: string;
  language_detected?: string;
}

export interface ImageChatResponse extends ChatResponse {
  raw_ocr_text?: string;
}

// ---------------------------------------------------------------------------
// Language configuration
// ---------------------------------------------------------------------------

export type LanguageCode = "en" | "tw" | "ha" | "pcm" | "sw";

export interface LanguageConfig {
  code: LanguageCode;
  name: string;
  nativeName: string;
  /** BCP-47 tag for Web Speech API */
  speechCode: string;
  /** BCP-47 tag for SpeechSynthesis API */
  synthesisCode: string;
}

export const LANGUAGES: LanguageConfig[] = [
  {
    code: "en",
    name: "English",
    nativeName: "English",
    speechCode: "en-GH",
    synthesisCode: "en-GH",
  },
  {
    code: "tw",
    name: "Twi",
    nativeName: "Twi (Akan)",
    speechCode: "ak-GH",
    synthesisCode: "ak-GH",
  },
  {
    code: "ha",
    name: "Hausa",
    nativeName: "Hausa",
    speechCode: "ha-NG",
    synthesisCode: "ha-NG",
  },
  {
    code: "pcm",
    name: "Pidgin",
    nativeName: "Pidgin English",
    speechCode: "en-NG",
    synthesisCode: "en-NG",
  },
  {
    code: "sw",
    name: "Swahili",
    nativeName: "Kiswahili",
    speechCode: "sw-KE",
    synthesisCode: "sw-KE",
  },
];

// ---------------------------------------------------------------------------
// UI state types
// ---------------------------------------------------------------------------

export type VoiceState = "idle" | "listening" | "processing" | "done" | "error";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

export interface AppNotification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
  timestamp: Date;
}
