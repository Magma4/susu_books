"use client";
/**
 * Susu Books — Main Dashboard Page
 *
 * Three-zone layout:
 *   Zone 1 (top bar): Logo, date, language selector
 *   Zone 2 (main): Transaction feed (left) + Summary/Alerts (right)
 *   Zone 3 (bottom bar): Camera button, Voice button, Text input toggle
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

import { useVoiceInput } from "@/hooks/useVoiceInput";
import { useVoiceOutput } from "@/hooks/useVoiceOutput";
import { useApi } from "@/hooks/useApi";

import { sendChat } from "@/lib/api";
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
  return Math.random().toString(36).slice(2, 11);
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
  const [notification, setNotification] = useState<{
    type: "success" | "error" | "info";
    message: string;
  } | null>(null);

  const textInputRef = useRef<HTMLInputElement>(null);
  const notifTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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
  } = useApi();

  // ---------------------------------------------------------------------------
  // Speech synthesis
  // ---------------------------------------------------------------------------
  const langConfig = LANGUAGES.find((l) => l.code === language) ?? LANGUAGES[0];

  const { speak, isSpeaking } = useVoiceOutput({
    defaultLang: langConfig.synthesisCode,
    rate: 0.9,
  });

  // ---------------------------------------------------------------------------
  // Core: process a text message through the AI
  // ---------------------------------------------------------------------------
  const processMessage = useCallback(
    async (message: string) => {
      if (!message.trim()) return;

      // Add user bubble to chat
      const userMsg: ChatMessage = {
        id: makeId(),
        role: "user",
        content: message.trim(),
        timestamp: new Date(),
      };
      setChatMessages((prev) => [...prev, userMsg]);
      setIsProcessingChat(true);

      try {
        // Build conversation history for context (last 6 messages)
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

        // Ingest any transactions that were recorded
        if (res.transactions.length > 0) {
          ingestTransactions(res.transactions);
          showNotif("success", `${res.transactions.length} transaction(s) recorded`);
        }

        // Speak the response
        speak(res.response, langConfig.synthesisCode);
      } catch (e) {
        const errMsg =
          e instanceof Error ? e.message : "Something went wrong. Try again.";
        const errBubble: ChatMessage = {
          id: makeId(),
          role: "assistant",
          content: errMsg,
          timestamp: new Date(),
        };
        setChatMessages((prev) => [...prev, errBubble]);
        showNotif("error", errMsg);
      } finally {
        setIsProcessingChat(false);
      }
    },
    [chatMessages, language, langConfig.synthesisCode, ingestTransactions, speak]
  );

  // ---------------------------------------------------------------------------
  // Voice input
  // ---------------------------------------------------------------------------
  const handleVoiceFinal = useCallback(
    async (transcript: string) => {
      await processMessage(transcript);
    },
    [processMessage]
  );

  const {
    voiceState,
    interimTranscript,
    isSupported: voiceSupported,
    error: voiceError,
    toggleListening,
    stopListening,
    reset: resetVoice,
  } = useVoiceInput({
    language: langConfig.speechCode,
    onFinal: handleVoiceFinal,
    onError: (err) => showNotif("error", err),
  });

  // While processing chat from voice, keep the voice state in "processing"
  // The actual voiceState machine handles its own states; we overlay isProcessingChat
  const displayVoiceState =
    isProcessingChat && voiceState === "done" ? "processing" : voiceState;

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
        showNotif(
          "success",
          `Found ${res.transactions.length} transaction(s) in photo`
        );
      }

      speak(res.response, langConfig.synthesisCode);
    },
    [ingestTransactions, speak, langConfig.synthesisCode]
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

  // ---------------------------------------------------------------------------
  // Notifications
  // ---------------------------------------------------------------------------
  const showNotif = useCallback(
    (type: "success" | "error" | "info", message: string) => {
      setNotification({ type, message });
      if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
      notifTimerRef.current = setTimeout(() => setNotification(null), 4000);
    },
    []
  );

  // Focus text input when expanded
  useEffect(() => {
    if (showTextInput) {
      setTimeout(() => textInputRef.current?.focus(), 100);
    }
  }, [showTextInput]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (notifTimerRef.current) clearTimeout(notifTimerRef.current);
    };
  }, []);

  // ---------------------------------------------------------------------------
  // Render
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
            <div className="h-8 w-8 bg-primary-900 rounded-xl flex items-center justify-center">
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

          {/* Date */}
          <p className="text-xs text-text-secondary hidden sm:block">
            {formatHeaderDate()}
          </p>

          {/* Right controls */}
          <div className="flex items-center gap-3">
            {/* Online indicator */}
            <div
              className={`h-2 w-2 rounded-full flex-shrink-0 ${
                backendOnline ? "bg-primary-light" : "bg-danger animate-pulse"
              }`}
              title={backendOnline ? "AI online" : "AI offline"}
            />
            <LanguageSelector value={language} onChange={setLanguage} />
          </div>
        </div>
      </header>

      {/* ------------------------------------------------------------------ */}
      {/* ZONE 2 — Main Content                                              */}
      {/* ------------------------------------------------------------------ */}
      <main
        className="zone-main flex-1 overflow-y-auto overscroll-contain"
        style={{ paddingBottom: showTextInput ? "200px" : "140px" }}
      >
        <div className="max-w-7xl mx-auto p-3 sm:p-4 lg:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 lg:gap-5">

            {/* Left column — Transaction feed (60%) */}
            <div className="lg:col-span-3 order-2 lg:order-1">
              <TransactionFeed
                transactions={transactions}
                isLoading={isLoadingInitial}
              />
            </div>

            {/* Right column — Summary + Alerts (40%) */}
            <div className="lg:col-span-2 order-1 lg:order-2 space-y-4">
              {/* Daily P&L */}
              <DailySummary
                data={dailySummary}
                isLoading={isLoadingInitial}
              />

              {/* 7-day sparkline */}
              {weeklyReport && (
                <WeeklySpark
                  data={weeklyReport.daily_trend}
                  currency="GHS"
                />
              )}

              {/* Inventory */}
              <InventoryPanel
                items={inventory}
                isLoading={isLoadingInitial}
              />

              {/* Action alerts */}
              <ActionPanel
                alerts={inventoryAlerts}
                summary={dailySummary}
                backendOnline={backendOnline}
              />

              {/* Chat history */}
              {chatMessages.length > 0 && (
                <ChatBubble
                  messages={chatMessages}
                  isTyping={isProcessingChat}
                />
              )}
            </div>
          </div>
        </div>
      </main>

      {/* ------------------------------------------------------------------ */}
      {/* ZONE 3 — Bottom Action Bar                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="zone-bottom bottom-bar flex-shrink-0 fixed bottom-0 left-0 right-0 z-30 bg-white/95 backdrop-blur-sm border-t border-border safe-bottom">
        <div className="max-w-2xl mx-auto px-4 pt-3 pb-4">

          {/* Text input — slides in when toggled */}
          {showTextInput && (
            <form
              onSubmit={handleTextSubmit}
              className="text-input-expanded flex items-center gap-2 mb-3"
            >
              <input
                ref={textInputRef}
                type="text"
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                placeholder="Type your transaction…"
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
                Send
              </button>
            </form>
          )}

          {/* Main button row */}
          <div className="flex items-center justify-center gap-5">
            {/* Camera */}
            <CameraButton
              language={language}
              onResponse={handleImageResponse}
              onError={(msg) => showNotif("error", msg)}
              disabled={isProcessingChat}
            />

            {/* Voice (center, biggest) */}
            <VoiceButton
              voiceState={displayVoiceState}
              interimTranscript={interimTranscript}
              isSupported={voiceSupported}
              error={voiceError}
              onToggle={isProcessingChat ? () => {} : toggleListening}
              onStop={stopListening}
              disabled={isProcessingChat}
            />

            {/* Text input toggle */}
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
      {/* Toast notification                                                  */}
      {/* ------------------------------------------------------------------ */}
      {notification && (
        <div
          className={`
            fixed top-[70px] left-1/2 -translate-x-1/2 z-50
            px-4 py-2.5 rounded-xl shadow-card-hover text-sm font-medium
            animate-fade-in max-w-sm w-full mx-4
            ${
              notification.type === "success"
                ? "bg-primary-surface text-primary-900 border border-primary-100"
                : notification.type === "error"
                ? "bg-red-50 text-danger border border-red-100"
                : "bg-white text-text-primary border border-border"
            }
          `}
          role="alert"
          aria-live="polite"
        >
          {notification.type === "success" && "✅ "}
          {notification.type === "error" && "⚠️ "}
          {notification.message}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Inline icons (keeps the component self-contained for the layout elements)
// ---------------------------------------------------------------------------

function BookIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5 text-white"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  );
}

function KeyboardIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="2" y="6" width="20" height="12" rx="2" />
      <line x1="6" y1="10" x2="6" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="10" y1="10" x2="10" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="14" y1="10" x2="14" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="18" y1="10" x2="18" y2="10" strokeWidth={3} strokeLinecap="round" />
      <line x1="6" y1="14" x2="18" y2="14" strokeWidth={3} strokeLinecap="round" />
    </svg>
  );
}
