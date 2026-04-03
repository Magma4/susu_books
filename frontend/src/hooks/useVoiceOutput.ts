"use client";
/**
 * Susu Books — useVoiceOutput hook
 * Wraps the browser SpeechSynthesis API to read AI responses aloud.
 * - Matches voice to user's selected language
 * - Falls back gracefully when synthesis isn't available
 * - Exposes speaking state for UI feedback
 */

import { useCallback, useEffect, useRef, useState } from "react";

export interface UseVoiceOutputReturn {
  /** Speak a text string in the given language */
  speak: (text: string, lang?: string) => void;
  /** Stop any current speech immediately */
  stop: () => void;
  /** True while the engine is speaking */
  isSpeaking: boolean;
  /** True if SpeechSynthesis is available in this browser */
  isSupported: boolean;
  /** Whether speech output is enabled (user can toggle off) */
  isEnabled: boolean;
  setEnabled: (v: boolean) => void;
}

interface UseVoiceOutputOptions {
  /** Default BCP-47 language / synthesis code */
  defaultLang?: string;
  /** Speech rate (0.1–10). Default 0.9 for clarity */
  rate?: number;
  /** Pitch (0–2). Default 1.0 */
  pitch?: number;
}

export function useVoiceOutput(
  options: UseVoiceOutputOptions = {}
): UseVoiceOutputReturn {
  const { defaultLang = "en-GH", rate = 0.9, pitch = 1.0 } = options;

  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [isEnabled, setEnabled] = useState(true);

  // Cache the best available voice per language to avoid re-querying
  const voiceCacheRef = useRef<Map<string, SpeechSynthesisVoice>>(new Map());
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setIsSupported(true);

      // Voices may load asynchronously on Chrome
      const populateCache = () => {
        const voices = window.speechSynthesis.getVoices();
        voiceCacheRef.current = buildVoiceCache(voices);
      };

      populateCache();
      window.speechSynthesis.addEventListener("voiceschanged", populateCache);
      return () => {
        window.speechSynthesis.removeEventListener("voiceschanged", populateCache);
      };
    }
  }, []);

  const speak = useCallback(
    (text: string, lang = defaultLang) => {
      if (!isSupported || !isEnabled || !text.trim()) return;

      // Cancel any in-progress speech
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang;
      utterance.rate = rate;
      utterance.pitch = pitch;
      utterance.volume = 1.0;

      // Assign best matching voice
      const bestVoice = findBestVoice(lang, voiceCacheRef.current);
      if (bestVoice) {
        utterance.voice = bestVoice;
      }

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    },
    [isSupported, isEnabled, defaultLang, rate, pitch]
  );

  const stop = useCallback(() => {
    if (!isSupported) return;
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  }, [isSupported]);

  // Stop speech when component unmounts
  useEffect(() => {
    return () => {
      if (isSupported) {
        window.speechSynthesis.cancel();
      }
    };
  }, [isSupported]);

  return { speak, stop, isSpeaking, isSupported, isEnabled, setEnabled };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Build a language → best voice mapping from available voices.
 * Prioritises exact match → language prefix match → default.
 */
function buildVoiceCache(
  voices: SpeechSynthesisVoice[]
): Map<string, SpeechSynthesisVoice> {
  const cache = new Map<string, SpeechSynthesisVoice>();
  const collected = new Map<string, SpeechSynthesisVoice[]>();

  for (const voice of voices) {
    const lang = voice.lang.toLowerCase();
    const prefix = lang.split("-")[0];
    if (!collected.has(prefix)) collected.set(prefix, []);
    collected.get(prefix)!.push(voice);
  }

  for (const [prefix, vList] of collected.entries()) {
    // Prefer non-default, then default
    const best =
      vList.find((v) => v.localService) ??
      vList.find((v) => v.default) ??
      vList[0];
    cache.set(prefix, best);
  }

  return cache;
}

function findBestVoice(
  lang: string,
  cache: Map<string, SpeechSynthesisVoice>
): SpeechSynthesisVoice | null {
  if (!("speechSynthesis" in window)) return null;
  const voices = window.speechSynthesis.getVoices();

  // 1. Exact BCP-47 match
  const exact = voices.find(
    (v) => v.lang.toLowerCase() === lang.toLowerCase()
  );
  if (exact) return exact;

  // 2. Language prefix match (e.g. "en" from "en-GH")
  const prefix = lang.split("-")[0].toLowerCase();
  const prefixMatch = voices.find((v) =>
    v.lang.toLowerCase().startsWith(prefix)
  );
  if (prefixMatch) return prefixMatch;

  // 3. Cache lookup
  return cache.get(prefix) ?? null;
}
