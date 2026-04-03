/**
 * Susu Books — Design Token System
 * Single source of truth for all colors, spacing, and visual constants.
 * These mirror the Tailwind config; use these in dynamic className logic.
 */

export const colors = {
  primary: {
    DEFAULT: "#1B5E20",
    light: "#4CAF50",
    surface: "#E8F5E9",
    hover: "#388E3C",
  },
  accent: {
    DEFAULT: "#F57F17",
    light: "#FFF8E1",
    hover: "#E65100",
    muted: "#FFB74D",
  },
  background: "#FAFAF5",
  surface: "#FFFFFF",
  border: "#E0E0E0",
  text: {
    primary: "#212121",
    secondary: "#616161",
    disabled: "#9E9E9E",
    inverse: "#FFFFFF",
  },
  semantic: {
    success: "#2E7D32",
    successBg: "#E8F5E9",
    warning: "#F9A825",
    warningBg: "#FFF8E1",
    danger: "#C62828",
    dangerBg: "#FFEBEE",
    info: "#1565C0",
    infoBg: "#E3F2FD",
  },
} as const;

// Transaction type color mapping
export const txColors = {
  sale: {
    icon: "↑",
    bg: "bg-primary-surface",
    text: "text-primary-800",
    badge: "bg-primary-surface text-primary-800",
    border: "border-primary-200",
    amount: "text-primary-800",
  },
  purchase: {
    icon: "↓",
    bg: "bg-accent-light",
    text: "text-accent-800",
    badge: "bg-accent-light text-accent-800",
    border: "border-amber-200",
    amount: "text-accent-800",
  },
  expense: {
    icon: "→",
    bg: "bg-red-50",
    text: "text-danger",
    badge: "bg-red-50 text-danger",
    border: "border-red-100",
    amount: "text-danger",
  },
} as const;

// Spacing constants for consistent layout
export const spacing = {
  cardPadding: "p-4",
  sectionGap: "gap-4",
  bottomBarHeight: "120px",
  topBarHeight: "60px",
} as const;

// Animation duration tokens
export const durations = {
  fast: 150,
  base: 300,
  slow: 600,
} as const;

// Voice button colors by state
export const voiceButtonColors = {
  idle: {
    bg: "bg-primary-900",
    shadow: "shadow-voice",
    ring: "",
  },
  listening: {
    bg: "bg-accent-800",
    shadow: "shadow-voice-listening",
    ring: "animate-pulse-ring",
  },
  processing: {
    bg: "bg-primary-700",
    shadow: "shadow-voice",
    ring: "",
  },
  done: {
    bg: "bg-success",
    shadow: "shadow-voice",
    ring: "",
  },
  error: {
    bg: "bg-danger",
    shadow: "",
    ring: "",
  },
} as const;

/**
 * Format a monetary amount for display.
 * @param amount - numeric amount
 * @param currency - currency code (GHS, KES, NGN, etc.)
 */
export function formatAmount(amount: number, currency = "GHS"): string {
  const symbols: Record<string, string> = {
    GHS: "₵",
    NGN: "₦",
    KES: "KSh",
    UGX: "USh",
    TZS: "TSh",
    XOF: "CFA",
    USD: "$",
  };
  const sym = symbols[currency] ?? currency + " ";
  return `${sym}${amount.toLocaleString("en-GH", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Format a datetime string to local time (e.g. "2:34 PM").
 */
export function formatTime(isoString: string): string {
  return new Date(isoString).toLocaleTimeString("en-GH", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/**
 * Format a date for display in the header (e.g. "Friday, April 4, 2026").
 */
export function formatHeaderDate(d: Date = new Date()): string {
  return d.toLocaleDateString("en-GH", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

/**
 * Return a human-readable relative time (e.g. "3 min ago", "just now").
 */
export function relativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

/**
 * Short date label for sparkline axis (e.g. "Mon", "Tue").
 */
export function shortDay(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString("en-GH", { weekday: "short" });
}
