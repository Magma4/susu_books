"use client";
/**
 * DemoMode — Auto-plays a scripted sequence of Ama's transactions.
 *
 * Shows each message "typing" character-by-character in the input area,
 * then submits it to the AI pipeline, creating a smooth demo recording
 * without requiring live voice input.
 *
 * The parent page passes `onMessage` — the same handler used for real voice input.
 */

import { useCallback, useEffect, useRef, useState } from "react";

// ---------------------------------------------------------------------------
// Demo script — Ama's Wednesday morning in Makola Market, Accra
// ---------------------------------------------------------------------------

export interface DemoStep {
  message: string;
  label: string;
  emoji: string;
  /** Pause before this step starts (ms) */
  preDelay: number;
  /** How fast to type (ms per character) */
  typeSpeed: number;
}

export const AMA_DEMO_SCRIPT: DemoStep[] = [
  {
    message: "I bought 10 bags of rice from Kofi for 120 cedis each",
    label: "Buying rice stock from Kofi",
    emoji: "🛒",
    preDelay: 1500,
    typeSpeed: 35,
  },
  {
    message: "Sold 3 bags of rice at 180 cedis each to Maame",
    label: "First sale of the day",
    emoji: "💚",
    preDelay: 2500,
    typeSpeed: 30,
  },
  {
    message: "I bought 4 crates of tomatoes from Abena for 50 cedis each",
    label: "Restocking tomatoes",
    emoji: "🛒",
    preDelay: 2000,
    typeSpeed: 32,
  },
  {
    message: "Sold 2 crates of tomatoes at 80 cedis each",
    label: "Tomato sales",
    emoji: "💚",
    preDelay: 2000,
    typeSpeed: 30,
  },
  {
    message: "Transport to market today cost 15 cedis",
    label: "Recording transport expense",
    emoji: "🚌",
    preDelay: 1800,
    typeSpeed: 28,
  },
  {
    message: "Sold 8 kg of onions at 12 cedis per kg",
    label: "Onion sales",
    emoji: "💚",
    preDelay: 2200,
    typeSpeed: 30,
  },
  {
    message: "I bought 10 liters of palm oil from Abena for 35 cedis each",
    label: "Restocking palm oil",
    emoji: "🛒",
    preDelay: 2000,
    typeSpeed: 32,
  },
  {
    message: "Sold 5 bunches of plantains at 38 cedis each to a customer",
    label: "Plantain sales",
    emoji: "💚",
    preDelay: 2000,
    typeSpeed: 30,
  },
  {
    message: "Market stall fee today was 8 cedis",
    label: "Market fee",
    emoji: "📋",
    preDelay: 1500,
    typeSpeed: 28,
  },
  {
    message: "How did I do today?",
    label: "Daily summary",
    emoji: "📊",
    preDelay: 2000,
    typeSpeed: 40,
  },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface DemoModeProps {
  /** Called for each scripted message — same as real voice/text handler */
  onMessage: (message: string) => Promise<void>;
  /** Called when demo completes all steps */
  onComplete?: () => void;
}

type DemoState = "idle" | "typing" | "waiting_ai" | "pausing" | "complete";

export default function DemoMode({ onMessage, onComplete }: DemoModeProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [demoState, setDemoState] = useState<DemoState>("idle");
  const [typedText, setTypedText] = useState("");

  const abortRef = useRef(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const stepRef = useRef(0);

  const clearTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Type a single character at a time
  // ---------------------------------------------------------------------------
  const typeMessage = useCallback(
    (
      message: string,
      speed: number,
      onDone: () => void
    ) => {
      let charIdx = 0;
      setTypedText("");

      const typeNext = () => {
        if (abortRef.current) return;
        if (charIdx >= message.length) {
          onDone();
          return;
        }
        setTypedText(message.slice(0, charIdx + 1));
        charIdx++;
        timeoutRef.current = setTimeout(typeNext, speed + Math.random() * 10);
      };
      timeoutRef.current = setTimeout(typeNext, speed);
    },
    []
  );

  // ---------------------------------------------------------------------------
  // Run one step
  // ---------------------------------------------------------------------------
  const runStep = useCallback(
    async (stepIndex: number) => {
      if (abortRef.current || stepIndex >= AMA_DEMO_SCRIPT.length) {
        setDemoState("complete");
        setIsRunning(false);
        onComplete?.();
        return;
      }

      const step = AMA_DEMO_SCRIPT[stepIndex];
      stepRef.current = stepIndex;
      setCurrentStep(stepIndex);

      // Pre-delay pause
      setDemoState("pausing");
      await new Promise<void>((resolve) => {
        timeoutRef.current = setTimeout(() => {
          if (!abortRef.current) resolve();
        }, step.preDelay);
      });
      if (abortRef.current) return;

      // Type the message
      setDemoState("typing");
      await new Promise<void>((resolve) => {
        typeMessage(step.message, step.typeSpeed, resolve);
      });
      if (abortRef.current) return;

      // Brief pause after typing
      await new Promise<void>((resolve) => {
        timeoutRef.current = setTimeout(() => {
          if (!abortRef.current) resolve();
        }, 600);
      });
      if (abortRef.current) return;

      // Send to AI
      setDemoState("waiting_ai");
      try {
        await onMessage(step.message);
      } catch {
        // Errors are handled upstream; continue demo
      }

      if (!abortRef.current) {
        setTypedText("");
        runStep(stepIndex + 1);
      }
    },
    [typeMessage, onMessage, onComplete]
  );

  // ---------------------------------------------------------------------------
  // Start / stop
  // ---------------------------------------------------------------------------
  const start = useCallback(() => {
    abortRef.current = false;
    setIsRunning(true);
    setCurrentStep(0);
    setTypedText("");
    setDemoState("pausing");
    runStep(0);
  }, [runStep]);

  const stop = useCallback(() => {
    abortRef.current = true;
    clearTimer();
    setIsRunning(false);
    setDemoState("idle");
    setTypedText("");
  }, [clearTimer]);

  const restart = useCallback(() => {
    stop();
    setTimeout(start, 300);
  }, [stop, start]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      abortRef.current = true;
      clearTimer();
    };
  }, [clearTimer]);

  const step = AMA_DEMO_SCRIPT[currentStep];
  const progressPct = ((currentStep + (demoState === "complete" ? 1 : 0)) / AMA_DEMO_SCRIPT.length) * 100;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="w-full">
      {/* Demo toggle button (shown when not running) */}
      {!isRunning && demoState !== "complete" && (
        <button
          onClick={start}
          className="
            w-full py-2.5 px-4 rounded-xl border-2 border-dashed border-accent-800
            text-accent-800 text-sm font-semibold hover:bg-accent-light
            transition-colors flex items-center justify-center gap-2
          "
        >
          <span>▶</span>
          Watch Demo — Ama&apos;s Day
        </button>
      )}

      {/* Demo complete */}
      {demoState === "complete" && (
        <div className="flex items-center gap-2">
          <div className="flex-1 text-center py-2 bg-primary-surface rounded-xl text-sm text-primary-800 font-semibold">
            ✅ Demo complete!
          </div>
          <button
            onClick={restart}
            className="py-2 px-3 rounded-xl border border-border text-xs text-text-secondary hover:bg-gray-50"
          >
            Replay
          </button>
        </div>
      )}

      {/* Running panel */}
      {isRunning && step && (
        <div className="bg-accent-light border border-amber-200 rounded-2xl p-3 space-y-2">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="text-base">{step.emoji}</span>
              <span className="text-xs font-semibold text-accent-900">
                Demo — Ama&apos;s Day
              </span>
              <span className="text-2xs text-accent-800 bg-white/60 px-1.5 py-0.5 rounded-full">
                {currentStep + 1}/{AMA_DEMO_SCRIPT.length}
              </span>
            </div>
            <button
              onClick={stop}
              className="text-2xs text-accent-800 hover:text-accent-900 font-medium"
            >
              Stop
            </button>
          </div>

          {/* Step label */}
          <p className="text-xs text-accent-800 font-medium">{step.label}</p>

          {/* Typing text display */}
          {typedText && (
            <div className="bg-white/80 rounded-lg px-3 py-2">
              <p className="text-sm text-text-primary font-medium">
                &ldquo;{typedText}
                {demoState === "typing" && (
                  <span className="inline-block w-0.5 h-4 bg-accent-800 ml-0.5 animate-pulse align-middle" />
                )}
                &rdquo;
              </p>
            </div>
          )}

          {/* Waiting indicator */}
          {demoState === "waiting_ai" && (
            <div className="flex items-center gap-1.5 text-xs text-accent-800">
              <span className="h-3 w-3 border border-accent-800 border-t-transparent rounded-full animate-spin" />
              Susu Books is thinking…
            </div>
          )}

          {/* Progress bar */}
          <div className="h-1 bg-white/50 rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-800 rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
