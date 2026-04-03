"use client";
/**
 * VoiceButton — The primary interaction element for Susu Books.
 *
 * States:
 *   idle        → green mic, tap to start listening
 *   listening   → amber pulse ring + live waveform bars + live transcript
 *   processing  → spinning ring, "Thinking…" label
 *   done        → brief green checkmark flash, then returns to idle
 *   error       → red mic, error message, tap to retry
 *
 * Supports both tap-to-toggle and hold-to-speak (press + release).
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { VoiceState } from "@/lib/types";
import LoadingPulse from "./LoadingPulse";

interface VoiceButtonProps {
  voiceState: VoiceState;
  interimTranscript: string;
  isSupported: boolean;
  error: string | null;
  onToggle: () => void;
  onStop: () => void;
  disabled?: boolean;
}

export default function VoiceButton({
  voiceState,
  interimTranscript,
  isSupported,
  error,
  onToggle,
  onStop,
  disabled = false,
}: VoiceButtonProps) {
  const [showDone, setShowDone] = useState(false);
  const holdTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isHoldingRef = useRef(false);

  // Flash "done" checkmark briefly when state transitions to done
  useEffect(() => {
    if (voiceState === "done") {
      setShowDone(true);
      const timer = setTimeout(() => setShowDone(false), 1200);
      return () => clearTimeout(timer);
    }
  }, [voiceState]);

  // Hold-to-speak: start after 200ms hold
  const handlePointerDown = useCallback(() => {
    if (disabled || voiceState === "processing") return;
    isHoldingRef.current = true;
    holdTimerRef.current = setTimeout(() => {
      if (isHoldingRef.current && voiceState === "idle") {
        onToggle(); // start listening
      }
    }, 200);
  }, [disabled, voiceState, onToggle]);

  const handlePointerUp = useCallback(() => {
    if (holdTimerRef.current) clearTimeout(holdTimerRef.current);
    if (isHoldingRef.current) {
      isHoldingRef.current = false;
      if (voiceState === "listening") {
        onStop(); // stop and process
      }
    }
  }, [voiceState, onStop]);

  const handleClick = useCallback(() => {
    if (disabled || voiceState === "processing") return;
    // Tap-to-toggle (when not in hold mode)
    if (!isHoldingRef.current) {
      onToggle();
    }
  }, [disabled, voiceState, onToggle]);

  // Button appearance by state
  const { bg, ring, icon, label } = getButtonConfig(voiceState, showDone, isSupported);

  const isListening = voiceState === "listening";
  const isProcessing = voiceState === "processing";

  return (
    <div className="flex flex-col items-center gap-3">
      {/* Live transcript / status label */}
      <div className="min-h-[36px] flex items-center justify-center px-4">
        <TranscriptDisplay
          voiceState={voiceState}
          interimTranscript={interimTranscript}
          error={error}
          isSupported={isSupported}
        />
      </div>

      {/* The big button */}
      <div className="relative flex items-center justify-center">
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
          onPointerDown={handlePointerDown}
          onPointerUp={handlePointerUp}
          onPointerLeave={handlePointerUp}
          disabled={disabled || !isSupported || isProcessing}
          aria-label={label}
          aria-pressed={isListening}
          className={`
            relative z-10 h-20 w-20 rounded-full flex items-center justify-center
            transition-all duration-200 select-none touch-none
            focus:outline-none focus-visible:ring-4 focus-visible:ring-offset-2 focus-visible:ring-primary-light
            active:scale-95
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
              ? "0 4px 20px rgba(245,127,23,0.45), 0 2px 8px rgba(245,127,23,0.25)"
              : "0 4px 14px rgba(27,94,32,0.35), 0 2px 6px rgba(27,94,32,0.2)",
          }}
        >
          {/* Icon content */}
          {isProcessing ? (
            <LoadingPulse size="md" color="white" />
          ) : showDone ? (
            <CheckIcon />
          ) : isListening ? (
            <WaveformIcon />
          ) : (
            icon
          )}
        </button>
      </div>

      {/* State label */}
      <p
        className={`text-xs font-medium transition-colors duration-200 ${
          isListening
            ? "text-accent-800"
            : isProcessing
            ? "text-primary-700"
            : "text-text-secondary"
        }`}
      >
        {isListening
          ? "Listening… tap to stop"
          : isProcessing
          ? "Thinking…"
          : showDone
          ? "Got it!"
          : !isSupported
          ? "Voice not supported"
          : voiceState === "error"
          ? "Tap to retry"
          : "Tap to speak"}
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Transcript / status display
// ---------------------------------------------------------------------------

function TranscriptDisplay({
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
      <p className="text-xs text-text-disabled text-center max-w-xs">
        Your browser doesn&apos;t support voice input. Use the text field below.
      </p>
    );
  }
  if (voiceState === "error" && error) {
    return (
      <p className="text-xs text-danger text-center max-w-xs font-medium">
        {error}
      </p>
    );
  }
  if (voiceState === "listening" && interimTranscript) {
    return (
      <p className="text-sm text-text-primary text-center max-w-xs italic leading-snug animate-fade-in">
        &ldquo;{interimTranscript}&rdquo;
      </p>
    );
  }
  if (voiceState === "listening") {
    return (
      <p className="text-xs text-accent-800 text-center animate-pulse">
        Speak now…
      </p>
    );
  }
  if (voiceState === "processing") {
    return (
      <p className="text-xs text-text-secondary text-center animate-pulse">
        Processing your request…
      </p>
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
      label: "Stop listening",
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
      className={`h-8 w-8 text-white transition-transform duration-200 ${active ? "scale-110" : ""}`}
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
      className="h-9 w-9 text-white animate-fade-in"
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
  // Animated waveform bars shown while listening
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
