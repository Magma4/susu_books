"use client";
/**
 * Susu Books — Main Dashboard Page
 *
 * Three-zone layout:
 *   Zone 1 (top bar): Logo, date, demo toggle, language selector
 *   Zone 2 (main): Transaction feed (left) + Summary/Alerts (right)
 *   Zone 3 (bottom bar): Camera, Voice button, Text input, Demo panel
 *
 * Includes:
 *   - Ollama offline detection with friendly setup screen
 *   - Demo mode with scripted sequence of Ama's transactions
 *   - Graceful voice fallback to text input
 *   - Toast notifications for all error/success states
 */

import { useCallback, useEffect, useRef, useState } from "react";

import VoiceButton from "@/components/VoiceButton";
import CameraButton from "@/components/CameraButton";
import TransactionFeed from "@/components/TransactionFeed";
import DailySummary from "@/components/DailySummary";
import WeeklySpark from "@/components/WeeklySpark";
import InventoryPanel from "@/components/InventoryPanel";
import ActionPanel from "@/components/ActionPanel";
import ChatBubble from "@/components/ChatBubble";
import LanguageSelector from "@/components/LanguageSelector";
import OllamaOfflineScreen from "@/components/OllamaOfflineScreen";
import DemoMode from "@/components/DemoMode";

import { useVoiceInput } from "@/hooks/useVoiceInput";
import { useVoiceOutput } from "@/hooks/useVoiceOutput";
import { useApi } from "@/hooks/useApi";

import { sendChat, getHealth } from "@/lib/api";
import type {
  ChatMessage,
  LanguageCode,
  ChatResponse,
  ImageChatResponse,
} from "@/lib/types";
import { LANGUAGES } from "@/lib/types";
import { formatHeaderDate } from "@/styles/theme";

// Lightweight unique ID generator
function makeId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
}

// ---------------------------------------------------------------------------
// Toast notification type
// ---------------------------------------------------------------------------
interface Toast {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function HomePage() {
  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  const [language, setLanguage] = useState<LanguageCode>("en");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isProcessingChat, setIsProcessingChat] = useState(false);
  const [textInput, setTextInput] = useState("");
  const [showTextInput, setShowTextInput] = useState(false);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [isDemoMode, setIsDemoMode] = useState(false);
  const [isRetryingHealth, setIsRetryingHealth] = useState(false);

  // Connectivity state (more nuanced than just backendOnline)
  const [healthState, setHealthState] = useState<{
    checked: boolean;
    backendReachable: boolean;
    ollamaReachable: boolean;
    modelLoaded: boolean;
  }>({ checked: false, backendReachable: false, ollamaReachable: false, modelLoaded: false });

  const textInputRef = useRef<HTMLInputElement>(null);
  const toastTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  // ---------------------------------------------------------------------------
  // API data
  // ---------------------------------------------------------------------------
  const {
    transactions,
    inventory,
    dailySummary,
    weeklyReport,
    inventoryAlerts,
    backendOnline,
    isLoadingInitial,
    ingestTransactions,
    refreshToday,
    refreshAll,
  } = useApi();

  // ---------------------------------------------------------------------------
  // Health check (initial + manual retry)
  // ---------------------------------------------------------------------------
  const checkHealth = useCallback(async () => {
    try {
      const health = await getHealth();
      setHealthState({
        checked: true,
        backendReachable: true,
        ollamaReachable: health.ollama_reachable,
        modelLoaded: health.model_loaded,
      });
    } catch {
      setHealthState({
        checked: true,
        backendReachable: false,
        ollamaReachable: false,
        modelLoaded: false,
      });
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const handleRetryHealth = useCallback(async () => {
    setIsRetryingHealth(true);
    await checkHealth();
    if (healthState.backendReachable) {
      await refreshAll();
    }
    setIsRetryingHealth(false);
  }, [checkHealth, healthState.backendReachable, refreshAll]);

  // ---------------------------------------------------------------------------
  // Toast notifications
  // ---------------------------------------------------------------------------
  const addToast = useCallback(
    (type: Toast["type"], message: string, duration = 4000) => {
      const id = makeId();
      setToasts((prev) => [...prev.slice(-3), { id, type, message }]);
      const timer = setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
        toastTimersRef.current.delete(id);
      }, duration);
      toastTimersRef.current.set(id, timer);
    },
    []
  );

  useEffect(() => {
    return () => {
      toastTimersRef.current.forEach((t) => clearTimeout(t));
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Speech synthesis
  // ---------------------------------------------------------------------------
  const langConfig = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0];

  const { speak } = useVoiceOutput({
    defaultLang: langConfig.synthesisCode,
    rate: 0.9,
  });

  // ---------------------------------------------------------------------------
  // Core: process a message through the AI pipeline
  // ---------------------------------------------------------------------------
  const processMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      // Guard: if AI backend is unavailable, show error immediately
      if (!backendOnline) {
        addToast(
          "error",
          "AI is offline. Start Ollama and the backend, then try again.",
          6000
        );
        return;
      }

      // Add user bubble
      const userMsg: ChatMessage = {
        id: makeId(),
        role: "user",
        content: message.trim(),
        timestamp: new Date(),
      };
      setChatMessages((prev) => [...prev, userMsg]);
      setIsProcessingChat(true);

      try {
        const recentHistory = chatMessages.slice(-6).map((m) => ({
          role: m.role,
          content: m.content,
        }));

        const res: ChatResponse = await sendChat(
          message.trim(),
          language,
          recentHistory
        );

        // Add AI bubble
        const aiMsg: ChatMessage = {
          id: makeId(),
          role: "assistant",
          content: res.response,
          timestamp: new Date(),
        };
        setChatMessages((prev) => [...prev, aiMsg]);

        // Ingest any new transactions
        if (res.transactions.length > 0) {
          ingestTransactions(res.transactions);
          const names = res.transactions.map((t) => t.item).join(", ");
          addToast(
            "success",
            `Recorded: ${names} (${res.transactions.length} transaction${res.transactions.length > 1 ? "s" : ""})`
          );
        }

        // Show function call failures as toasts
        const failedCalls = res.function_calls.filter((fc) => !fc.success);
        for (const fc of failedCalls) {
          addToast(
            "warning",
            `Could not execute "${fc.name}": ${fc.error ?? "unknown error"}`,
            6000
          );
        }

        // Speak the response
        speak(res.response, langConfig.synthesisCode);
      } catch (e) {
        const errMsg = buildUserFriendlyError(e);
        const errBubble: ChatMessage = {
          id: makeId(),
          role: "assistant",
          content: errMsg,
          timestamp: new Date(),
        };
        setChatMessages((prev) => [...prev, errBubble]);
        addToast("error", errMsg, 6000);
      } finally {
        setIsProcessingChat(false);
      }
    },
    [chatMessages, language, langConfig.synthesisCode, ingestTransactions, speak, backendOnline, addToast]
  );

  // ---------------------------------------------------------------------------
  // Voice input
  // ---------------------------------------------------------------------------
  const handleVoiceFinal = useCallback(
    async (transcript: string) => {
      if (!transcript.trim()) return;
      await processMessage(transcript);
    },
    [processMessage]
  );

  const handleVoiceError = useCallback(
    (err: string) => {
      // If voice fails, automatically show text input as fallback
      if (err.includes("denied") || err.includes("not available") || err.includes("not supported")) {
        setShowTextInput(true);
        addToast(
          "info",
          "I couldn't access the microphone — try typing instead",
          5000
        );
      } else if (!err.includes("aborted")) {
        addToast("warning", err, 4000);
      }
    },
    [addToast]
  );

  const {
    voiceState,
    interimTranscript,
    isSupported: voiceSupported,
    error: voiceError,
    toggleListening,
    stopListening,
    reset,
  } = useVoiceInput({
    language: langConfig.speechCode,
    onFinal: handleVoiceFinal,
    onError: handleVoiceError,
  });

  // Show text fallback automatically when voice is unsupported
  useEffect(() => {
    if (!voiceSupported) setShowTextInput(true);
  }, [voiceSupported]);

  const displayVoiceState =
    isProcessingChat && voiceState === "done" ? "processing" : voiceState;

  // Auto-reset voice button to idle once AI finishes processing
  useEffect(() => {
    if (!isProcessingChat && voiceState === "done") {
      const t = setTimeout(() => reset(), 1500);
      return () => clearTimeout(t);
    }
  }, [isProcessingChat, voiceState, reset]);

  // ---------------------------------------------------------------------------
  // Image/OCR handler
  // ---------------------------------------------------------------------------
  const handleImageResponse = useCallback(
    (res: ImageChatResponse) => {
      const aiMsg: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: res.response,
        timestamp: new Date(),
      };
      setChatMessages((prev) => [...prev, aiMsg]);

      if (res.transactions.length > 0) {
        ingestTransactions(res.transactions);
        addToast(
          "success",
          `Found ${res.transactions.length} transaction${res.transactions.length > 1 ? "s" : ""} in photo`
        );
      } else {
        addToast(
          "info",
          "I couldn't read any clear transactions from this photo. Try better lighting.",
          5000
        );
      }

      speak(res.response, langConfig.synthesisCode);
    },
    [ingestTransactions, speak, langConfig.synthesisCode, addToast]
  );

  const handleImageError = useCallback(
    (msg: string) => {
      if (msg.toLowerCase().includes("blur") || msg.toLowerCase().includes("read")) {
        addToast(
          "warning",
          "I couldn't read this clearly. Try taking another photo with better lighting.",
          5000
        );
      } else {
        addToast("error", msg, 5000);
      }
    },
    [addToast]
  );

  // ---------------------------------------------------------------------------
  // Text input submit
  // ---------------------------------------------------------------------------
  const handleTextSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!textInput.trim() || isProcessingChat) return;
      const msg = textInput;
      setTextInput("");
      await processMessage(msg);
    },
    [textInput, isProcessingChat, processMessage]
  );

  // Focus text input when expanded
  useEffect(() => {
    if (showTextInput) {
      setTimeout(() => textInputRef.current?.focus(), 100);
    }
  }, [showTextInput]);

  // ---------------------------------------------------------------------------
  // Offline screen logic
  // ---------------------------------------------------------------------------
  const isFullyOffline =
    healthState.checked && !healthState.backendReachable;

  const isOllamaOnly =
    healthState.checked &&
    healthState.backendReachable &&
    !healthState.ollamaReachable;

  if (isFullyOffline) {
    return (
      <OllamaOfflineScreen
        isBackendDown={true}
        onRetry={handleRetryHealth}
        isRetrying={isRetryingHealth}
      />
    );
  }

  if (isOllamaOnly) {
    return (
      <OllamaOfflineScreen
        isBackendDown={false}
        onRetry={handleRetryHealth}
        isRetrying={isRetryingHealth}
      />
    );
  }

  // ---------------------------------------------------------------------------
  // Render — main dashboard
  // ---------------------------------------------------------------------------
  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">

      {/* ------------------------------------------------------------------ */}
      {/* ZONE 1 — Top Bar                                                   */}
      {/* ------------------------------------------------------------------ */}
      <header className="zone-header flex-shrink-0 bg-white/95 backdrop-blur-sm border-b border-border z-30 px-4 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          {/* Logo */}
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 bg-primary-900 rounded-xl flex items-center justify-center shadow-sm">
              <BookIcon />
            </div>
            <div>
              <h1 className="font-semibold text-text-primary leading-tight text-sm">
                Susu Books
              </h1>
              <p className="text-2xs text-text-disabled leading-tight hidden xs:block">
                Your business copilot
              </p>
            </div>
          </div>

          {/* Center: date */}
          <p className="text-xs text-text-secondary hidden sm:block">
            {formatHeaderDate()}
          </p>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            {/* Backend status dot */}
            <div
              className={`h-2 w-2 rounded-full flex-shrink-0 transition-colors duration-500 ${
                backendOnline ? "bg-primary-light" : "bg-warning animate-pulse"
              }`}
              title={backendOnline ? "AI online" : "AI offline"}
            />

            {/* Demo mode toggle */}
            <button
              onClick={() => setIsDemoMode((v) => !v)}
              className={`
                text-xs font-semibold px-2.5 py-1 rounded-full border transition-all duration-200
                ${
                  isDemoMode
                    ? "bg-accent-800 text-white border-accent-800"
                    : "border-border text-text-secondary hover:border-accent-800 hover:text-accent-800"
                }
              `}
              title="Toggle demo mode"
            >
              Demo
            </button>

            <LanguageSelector value={language} onChange={setLanguage} />
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* ZONE 2 — Main Content                                              */}
      {/* ------------------------------------------------------------------ */}
      <main
        className="zone-main flex-1 overflow-y-auto overscroll-contain"
        style={{ paddingBottom: showTextInput || isDemoMode ? "220px" : "150px" }}
      >
        <div className="max-w-7xl mx-auto p-3 sm:p-4 lg:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 lg:gap-5">

            {/* Left: Chat reply + Transaction feed (60%) */}
            <div className="lg:col-span-3 order-2 lg:order-1 space-y-4">
              {/* AI conversation — shown above the ledger when active */}
              {(chatMessages.length > 0 || isProcessingChat) && (
                <ChatBubble
                  messages={chatMessages.slice(-6)}
                  isTyping={isProcessingChat}
                />
              )}

              <TransactionFeed
                transactions={transactions}
                isLoading={isLoadingInitial}
              />
            </div>

            {/* Right: Summary + Alerts (40%) */}
            <div className="lg:col-span-2 order-1 lg:order-2 space-y-4">
              <DailySummary data={dailySummary} isLoading={isLoadingInitial} />

              {weeklyReport && weeklyReport.daily_trend.length > 0 && (
                <WeeklySpark data={weeklyReport.daily_trend} currency="GHS" />
              )}

              <InventoryPanel items={inventory} isLoading={isLoadingInitial} />

              <ActionPanel
                alerts={inventoryAlerts}
                summary={dailySummary}
                backendOnline={backendOnline}
              />
            </div>
          </div>
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* ZONE 3 — Bottom Action Bar                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="zone-bottom bottom-bar flex-shrink-0 fixed bottom-0 left-0 right-0 z-30 bg-white/95 backdrop-blur-sm border-t border-border safe-bottom">
        <div className="max-w-2xl mx-auto px-4 pt-3 pb-4 space-y-2">

          {/* Demo mode panel */}
          {isDemoMode && (
            <DemoMode
              onMessage={processMessage}
              onComplete={() => {
                addToast("success", "Demo complete! Susu Books works offline with your voice.");
              }}
            />
          )}

          {/* Text input */}
          {showTextInput && (
            <form
              onSubmit={handleTextSubmit}
              className="text-input-expanded flex items-center gap-2"
            >
              <input
                ref={textInputRef}
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder={
                  voiceSupported
                    ? "Type your transaction…"
                    : "Voice not supported — type here"
                }
                disabled={isProcessingChat}
                className="
                  flex-1 rounded-xl border border-border px-4 py-2.5 text-sm
                  bg-background placeholder:text-text-disabled
                  focus:outline-none focus:ring-2 focus:ring-primary-light focus:border-transparent
                  disabled:opacity-50
                "
              />
              <button
                type="submit"
                disabled={!textInput.trim() || isProcessingChat}
                className="btn-primary px-4 py-2.5"
              >
                {isProcessingChat ? (
                  <span className="h-4 w-4 border-2 border-white/40 border-t-white rounded-full animate-spin block" />
                ) : (
                  "Send"
                )}
              </button>
            </form>
          )}

          {/* Main button row */}
          <div className="flex items-center justify-center gap-5">
            {/* Camera */}
            <CameraButton
              language={language}
              onResponse={handleImageResponse}
              onError={handleImageError}
              disabled={isProcessingChat}
            />

            {/* Voice (center) */}
            <VoiceButton
              voiceState={displayVoiceState}
              interimTranscript={interimTranscript}
              isSupported={voiceSupported}
              error={voiceError}
              onToggle={isProcessingChat ? () => {} : toggleListening}
              onStop={stopListening}
              disabled={isProcessingChat}
            />

            {/* Text toggle */}
            <button
              type="button"
              onClick={() => setShowTextInput((v) => !v)}
              aria-label={showTextInput ? "Close text input" : "Type instead"}
              aria-expanded={showTextInput}
              className={`
                h-14 w-14 rounded-full flex items-center justify-center
                border-2 transition-all duration-200
                ${
                  showTextInput
                    ? "border-primary-900 bg-primary-surface text-primary-900"
                    : "border-border text-text-secondary hover:border-text-secondary hover:text-text-primary"
                }
              `}
            >
              <KeyboardIcon />
            </button>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Toast Notifications                                                 */}
      {/* ------------------------------------------------------------------ */}
      <div
        className="fixed top-[68px] left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-full max-w-sm px-4 pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <ToastItem
            key={toast.id}
            toast={toast}
            onDismiss={() =>
              setToasts((prev) => prev.filter((t) => t.id !== toast.id))
            }
          />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Toast item component
// ---------------------------------------------------------------------------

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: Toast;
  onDismiss: () => void;
}) {
  const styles = {
    success: "bg-primary-surface text-primary-900 border-primary-100",
    error: "bg-red-50 text-danger border-red-100",
    warning: "bg-accent-light text-accent-900 border-amber-100",
    info: "bg-blue-50 text-blue-900 border-blue-100",
  };
  const icons = { success: "✅", error: "⚠️", warning: "⚡", info: "💡" };

  return (
    <div
      className={`
        pointer-events-auto flex items-start gap-2 px-3 py-2.5 rounded-xl
        border shadow-card-hover text-sm font-medium animate-slide-in
        ${styles[toast.type]}
      `}
      role="alert"
    >
      <span className="flex-shrink-0">{icons[toast.type]}</span>
      <p className="flex-1 leading-snug">{toast.message}</p>
      <button
        onClick={onDismiss}
        className="flex-shrink-0 opacity-40 hover:opacity-70 text-lg leading-none"
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error message helpers
// ---------------------------------------------------------------------------

function buildUserFriendlyError(e: unknown): string {
  if (!e) return "Something went wrong. Please try again.";
  const msg = e instanceof Error ? e.message : String(e);

  if (msg.includes("502") || msg.includes("Bad Gateway")) {
    return "The AI is thinking but took too long. Try again in a moment.";
  }
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    return "Can't reach the server. Is the backend running on port 8000?";
  }
  if (msg.includes("Ollama") || msg.includes("11434")) {
    return "The AI engine (Ollama) isn't responding. Make sure it's running.";
  }
  if (msg.includes("blurry") || msg.includes("OCR")) {
    return "I couldn't read this clearly. Try taking another photo with better lighting.";
  }
  return msg.length > 120 ? msg.slice(0, 117) + "…" : msg;
}

// ---------------------------------------------------------------------------
// Inline icons
// ---------------------------------------------------------------------------

function BookIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function KeyboardIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <line x1="6" y1="10" x2="6" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="10" y1="10" x2="10" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="14" y1="10" x2="14" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="18" y1="10" x2="18" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="6" y1="14" x2="18" y2="14" strokeWidth={3} strokeLinecap="round" />
    </svg>
  );
}
