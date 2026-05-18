"use client";
/**
 * Susu Books — useVoiceInput hook
 * Wraps the browser Web Speech API (SpeechRecognition) with:
 * - Graceful fallback when not supported
 * - Live interim transcript display
 * - Language switching
 * - Seller-controlled recording: browser auto-ends are restarted until the user taps stop
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { VoiceState } from "@/lib/types";

export interface UseVoiceInputReturn {
  /** Current state of the voice capture pipeline */
  voiceState: VoiceState;
  /** Final confirmed transcript (set on recognition end) */
  transcript: string;
  /** Live interim transcript while speaking */
  interimTranscript: string;
  /** Whether the browser supports speech recognition */
  isSupported: boolean;
  /** Start listening */
  startListening: () => void;
  /** Stop listening (fires onFinal with current transcript) */
  stopListening: () => void;
  /** Toggle between listening and idle */
  toggleListening: () => void;
  /** Reset to idle state and clear transcripts */
  reset: () => void;
  /** Any error message */
  error: string | null;
}

interface UseVoiceInputOptions {
  /** BCP-47 language code for recognition (e.g. "en-GH", "ha-NG") */
  language?: string;
  /** Called when a final transcript is ready */
  onFinal?: (transcript: string) => void;
  /** Called when recognition errors */
  onError?: (error: string) => void;
}

export function useVoiceInput(options: UseVoiceInputOptions = {}): UseVoiceInputReturn {
  const { language = "en-GH", onFinal, onError } = options;

  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [transcript, setTranscript] = useState("");
  const [interimTranscript, setInterimTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSupported, setIsSupported] = useState(false);

  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const finalTranscriptRef = useRef("");
  const interimTranscriptRef = useRef("");
  const recognitionActiveRef = useRef(false);
  const shouldKeepListeningRef = useRef(false);
  const manuallyStoppingRef = useRef(false);
  const restartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearRestartTimer = useCallback(() => {
    if (restartTimerRef.current) {
      clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
  }, []);

  // Check browser support on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      setIsSupported(!!SR);
    }
  }, []);

  // Recreate recognition instance whenever language changes
  useEffect(() => {
    if (typeof window === "undefined") return;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    // Abort any in-flight recognition before replacing
    if (recognitionRef.current) {
      recognitionRef.current.onend = null;
      recognitionRef.current.abort();
    }
    clearRestartTimer();

    const recognition = new SR();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = language;

    recognition.onstart = () => {
      recognitionActiveRef.current = true;
      setVoiceState("listening");
      setError(null);
      setInterimTranscript("");
    };

    recognition.onresult = (event: SpeechRecognitionEvent) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        if (result.isFinal) {
          final += result[0].transcript;
        } else {
          interim += result[0].transcript;
        }
      }
      if (final) {
        finalTranscriptRef.current = [finalTranscriptRef.current, final.trim()]
          .filter(Boolean)
          .join(" ");
        setTranscript(finalTranscriptRef.current);
      }
      interimTranscriptRef.current = interim;
      setInterimTranscript(interim);
    };

    recognition.onend = () => {
      recognitionActiveRef.current = false;
      const interimAtEnd = interimTranscriptRef.current.trim();
      if (interimAtEnd) {
        finalTranscriptRef.current = [finalTranscriptRef.current, interimAtEnd]
          .filter(Boolean)
          .join(" ");
        setTranscript(finalTranscriptRef.current);
      }
      const finalText = finalTranscriptRef.current.trim();
      setInterimTranscript("");
      interimTranscriptRef.current = "";

      if (shouldKeepListeningRef.current && !manuallyStoppingRef.current) {
        setVoiceState("listening");
        clearRestartTimer();
        restartTimerRef.current = setTimeout(() => {
          if (!shouldKeepListeningRef.current || recognitionActiveRef.current) return;
          try {
            recognition.start();
          } catch (e) {
            console.warn("SpeechRecognition restart error:", e);
          }
        }, 250);
        return;
      }

      shouldKeepListeningRef.current = false;
      manuallyStoppingRef.current = false;
      if (finalText) {
        setTranscript(finalText);
        setVoiceState("done");
        onFinal?.(finalText);
      } else {
        setVoiceState("idle");
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      recognitionActiveRef.current = false;
      if (shouldKeepListeningRef.current && event.error === "no-speech") {
        setInterimTranscript("");
        setVoiceState("listening");
        return;
      }

      if (event.error === "aborted" && !manuallyStoppingRef.current) {
        return;
      }

      const msg = getErrorMessage(event.error);
      setError(msg);
      setVoiceState("error");
      setInterimTranscript("");
      shouldKeepListeningRef.current = false;
      manuallyStoppingRef.current = false;
      onError?.(msg);
    };

    recognitionRef.current = recognition;

    return () => {
      clearRestartTimer();
      shouldKeepListeningRef.current = false;
      recognition.onend = null;
      recognition.abort();
    };
  }, [language, onFinal, onError, clearRestartTimer]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    if (voiceState === "listening") return;

    clearRestartTimer();
    shouldKeepListeningRef.current = true;
    manuallyStoppingRef.current = false;
    setTranscript("");
    setInterimTranscript("");
    finalTranscriptRef.current = "";
    interimTranscriptRef.current = "";
    setError(null);
    setVoiceState("listening");

    try {
      recognitionRef.current.start();
    } catch (e) {
      // Ignore "already started" errors (can happen on rapid taps)
      console.warn("SpeechRecognition start error:", e);
    }
  }, [voiceState, clearRestartTimer]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    clearRestartTimer();
    shouldKeepListeningRef.current = false;
    manuallyStoppingRef.current = true;

    if (recognitionActiveRef.current) {
      recognitionRef.current.stop();
      return;
    }

    const finalText = (finalTranscriptRef.current || interimTranscriptRef.current).trim();
    setInterimTranscript("");
    interimTranscriptRef.current = "";
    manuallyStoppingRef.current = false;
    if (finalText) {
      setTranscript(finalText);
      setVoiceState("done");
      onFinal?.(finalText);
    } else {
      setVoiceState("idle");
    }
  }, [clearRestartTimer, onFinal]);

  const toggleListening = useCallback(() => {
    if (voiceState === "listening") {
      stopListening();
    } else if (voiceState === "idle" || voiceState === "error" || voiceState === "done") {
      startListening();
    }
  }, [voiceState, startListening, stopListening]);

  const reset = useCallback(() => {
    clearRestartTimer();
    shouldKeepListeningRef.current = false;
    manuallyStoppingRef.current = false;
    if (recognitionRef.current && voiceState === "listening") {
      recognitionRef.current.abort();
    }
    setVoiceState("idle");
    setTranscript("");
    setInterimTranscript("");
    setError(null);
    finalTranscriptRef.current = "";
    interimTranscriptRef.current = "";
  }, [voiceState, clearRestartTimer]);

  return {
    voiceState,
    transcript,
    interimTranscript,
    isSupported,
    startListening,
    stopListening,
    toggleListening,
    reset,
    error,
  };
}

// Helpers

function getErrorMessage(errorCode: string): string {
  const messages: Record<string, string> = {
    "no-speech": "No speech detected. Please try again.",
    "audio-capture": "Microphone not available. Check permissions.",
    "not-allowed": "Microphone access denied. Enable microphone in browser settings.",
    "network": "Network error during recognition. Are you offline?",
    "aborted": "Recording stopped.",
    "service-not-allowed": "Speech recognition not allowed in this context.",
    "bad-grammar": "Speech grammar error.",
    "language-not-supported": "Selected language not supported by your browser.",
  };
  return messages[errorCode] ?? `Speech error: ${errorCode}`;
}
