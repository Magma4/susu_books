"use client";
/**
 * VoiceButton — The primary interaction element for Susu Books.
 * Simplified to be a flat, circular button aligning perfectly with sibling controls.
 */

import { useCallback, useEffect, useState } from "react";
import type { VoiceState } from "@/lib/types";
import LoadingPulse from "./LoadingPulse";

interface VoiceButtonProps {
  voiceState: VoiceState;
  isSupported: boolean;
  onToggle: () => void;
  disabled?: boolean;
}

export default function VoiceButton({
  voiceState,
  isSupported,
  onToggle,
  disabled = false,
}: VoiceButtonProps) {
  const [showDone, setShowDone] = useState(false);

  // Flash "done" checkmark briefly when state transitions to done
  useEffect(() => {
    if (voiceState === "done") {
      setShowDone(true);
      const timer = setTimeout(() => setShowDone(false), 1200);
      return () => clearTimeout(timer);
    }
  }, [voiceState]);

  const handleClick = useCallback(() => {
    if (disabled || voiceState === "processing") return;
    onToggle();
  }, [disabled, voiceState, onToggle]);

  const { bg, ring, icon, label } = getButtonConfig(voiceState, showDone, isSupported);

  const isListening = voiceState === "listening";
  const isProcessing = voiceState === "processing";

  return (
    <div className="relative flex items-center justify-center flex-shrink-0">
      {/* Outer pulse ring — only visible while listening */}
      {isListening && (
        <span className="absolute inset-0 rounded-full bg-accent-800/20 animate-ping scale-150" />
      )}
      {isListening && (
        <span className="absolute inset-0 rounded-full bg-accent-800/10 animate-ping scale-125" style={{ animationDelay: "0.4s" }} />
      )}

      <button
        type="button"
        onClick={handleClick}
        disabled={disabled || !isSupported || isProcessing}
        aria-label={label}
        aria-pressed={isListening}
        className={`
          relative z-10 h-14 w-14 rounded-full flex items-center justify-center
          transition-all duration-200 select-none touch-none
          focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-2 focus-visible:ring-primary-light
          active:scale-95 shadow-sm
          ${bg}
          ${ring}
          ${
            disabled || !isSupported
              ? "opacity-40 cursor-not-allowed"
              : isProcessing
              ? "cursor-wait"
              : "cursor-pointer"
          }
        `}
        style={{
          boxShadow: isListening
            ? "0 4px 14px rgba(245,127,23,0.3), 0 2px 6px rgba(245,127,23,0.15)"
            : "0 4px 10px rgba(27,94,32,0.25), 0 2px 4px rgba(27,94,32,0.1)",
        }}
      >
        {isProcessing ? (
          <LoadingPulse size="sm" color="white" />
        ) : showDone ? (
          <CheckIcon />
        ) : isListening ? (
          <WaveformIcon />
        ) : (
          icon
        )}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Transcript Display — Rendered above the buttons in page.tsx for layout elegance
// ---------------------------------------------------------------------------

export function TranscriptDisplay({
  voiceState,
  interimTranscript,
  error,
  isSupported,
}: {
  voiceState: VoiceState;
  interimTranscript: string;
  error: string | null;
  isSupported: boolean;
}) {
  if (!isSupported) {
    return (
      <p className="text-xs text-text-disabled text-center max-w-md mx-auto leading-relaxed">
        Your browser doesn&apos;t support voice input. Use the text field.
      </p>
    );
  }
  if (voiceState === "error" && error) {
    return (
      <p className="text-xs text-danger text-center max-w-md mx-auto font-medium animate-fadeIn">
        {error}
      </p>
    );
  }
  if (voiceState === "listening" && interimTranscript) {
    return (
      <p className="text-sm font-medium text-primary-900 text-center max-w-md mx-auto italic leading-snug animate-fadeIn">
        &ldquo;{interimTranscript}&rdquo;
      </p>
    );
  }
  if (voiceState === "listening") {
    return (
      <div className="flex items-center justify-center gap-2 max-w-md mx-auto animate-pulse">
        <span className="h-1.5 w-1.5 rounded-full bg-accent-800 animate-ping" />
        <p className="text-xs text-accent-800 font-semibold tracking-wide uppercase">
          Listening… speak clearly
        </p>
      </div>
    );
  }
  if (voiceState === "processing") {
    return (
      <div className="flex items-center justify-center gap-2 max-w-md mx-auto animate-pulse">
        <span className="h-2 w-2 border-2 border-primary-800/40 border-t-primary-800 rounded-full animate-spin" />
        <p className="text-xs text-primary-900 font-semibold tracking-wide uppercase">
          Thinking…
        </p>
      </div>
    );
  }
  return null;
}

// ---------------------------------------------------------------------------
// Button config by state
// ---------------------------------------------------------------------------

function getButtonConfig(
  state: VoiceState,
  showDone: boolean,
  isSupported: boolean
): { bg: string; ring: string; icon: React.ReactNode; label: string } {
  if (showDone || state === "done") {
    return {
      bg: "bg-success",
      ring: "",
      icon: <CheckIcon />,
      label: "Transaction recorded",
    };
  }
  if (state === "listening") {
    return {
      bg: "bg-accent-800",
      ring: "ring-4 ring-accent-800/30",
      icon: <MicIcon active />,
      label: "Finish voice input",
    };
  }
  if (state === "processing") {
    return {
      bg: "bg-primary-700",
      ring: "",
      icon: null,
      label: "Processing",
    };
  }
  if (state === "error") {
    return {
      bg: "bg-danger",
      ring: "",
      icon: <MicIcon />,
      label: "Retry voice input",
    };
  }
  return {
    bg: "bg-primary-900 hover:bg-primary-700",
    ring: "",
    icon: <MicIcon />,
    label: isSupported ? "Start voice input" : "Voice not available",
  };
}

// ---------------------------------------------------------------------------
// Icons
// ---------------------------------------------------------------------------

function MicIcon({ active = false }: { active?: boolean }) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className={`h-6 w-6 text-white transition-transform duration-200 ${active ? "scale-110 animate-pulse" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-6 w-6 text-white animate-fade-in"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function WaveformIcon() {
  const bars = [
    { height: "h-3", delay: "0ms" },
    { height: "h-5", delay: "160ms" },
    { height: "h-7", delay: "80ms" },
    { height: "h-5", delay: "240ms" },
    { height: "h-3", delay: "120ms" },
  ];
  return (
    <div className="flex items-center gap-0.5" aria-hidden="true">
      {bars.map((bar, i) => (
        <span
          key={i}
          className={`w-1 ${bar.height} bg-white rounded-full animate-wave-bar`}
          style={{ animationDelay: bar.delay }}
        />
      ))}
    </div>
  );
}
