"use client";
/**
 * Susu Books — useVoiceInput hook
 * Wraps the browser Web Speech API (SpeechRecognition) with:
 * - Graceful fallback when not supported
 * - Live interim transcript display
 * - Language switching
 * - Clean state machine: idle → listening → done/error
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

    const recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.lang = language;

    recognition.onstart = () => {
      setVoiceState("listening");
      setError(null);
      setInterimTranscript("");
      finalTranscriptRef.current = "";
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
        finalTranscriptRef.current += final;
        setTranscript(finalTranscriptRef.current);
      }
      setInterimTranscript(interim);
    };

    recognition.onend = () => {
      const finalText = finalTranscriptRef.current.trim();
      setInterimTranscript("");
      if (finalText) {
        setTranscript(finalText);
        setVoiceState("done");
        onFinal?.(finalText);
      } else {
        setVoiceState("idle");
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      const msg = getErrorMessage(event.error);
      setError(msg);
      setVoiceState("error");
      setInterimTranscript("");
      onError?.(msg);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.onend = null;
      recognition.abort();
    };
  }, [language, onFinal, onError]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) return;
    if (voiceState === "listening") return;

    setTranscript("");
    setInterimTranscript("");
    finalTranscriptRef.current = "";
    setError(null);

    try {
      recognitionRef.current.start();
    } catch (e) {
      // Ignore "already started" errors (can happen on rapid taps)
      console.warn("SpeechRecognition start error:", e);
    }
  }, [voiceState]);

  const stopListening = useCallback(() => {
    if (!recognitionRef.current) return;
    recognitionRef.current.stop();
  }, []);

  const toggleListening = useCallback(() => {
    if (voiceState === "listening") {
      stopListening();
    } else if (voiceState === "idle" || voiceState === "error" || voiceState === "done") {
      startListening();
    }
  }, [voiceState, startListening, stopListening]);

  const reset = useCallback(() => {
    if (recognitionRef.current && voiceState === "listening") {
      recognitionRef.current.abort();
    }
    setVoiceState("idle");
    setTranscript("");
    setInterimTranscript("");
    setError(null);
    finalTranscriptRef.current = "";
  }, [voiceState]);

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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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
