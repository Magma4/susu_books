import type { LanguageCode } from "./types";

const SIMPLE_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bghana cedi(s)?\b/gi, "GHS"],
  [/\bcedi(s)?\b/gi, "GHS"],
  [/\bghana\b/gi, "GHS"],
  [/\bkilos?\b/gi, "kg"],
  [/\bkilograms?\b/gi, "kg"],
  [/\bkgs\b/gi, "kg"],
  [/\blitres?\b/gi, "liters"],
  [/\bltrs?\b/gi, "liters"],
  [/\bpalmoil\b/gi, "palm oil"],
  [/\bplantains\b/gi, "plantains"],
];

const NUMBER_WORDS: Record<string, string> = {
  zero: "0",
  one: "1",
  two: "2",
  three: "3",
  four: "4",
  five: "5",
  six: "6",
  seven: "7",
  eight: "8",
  nine: "9",
  ten: "10",
  eleven: "11",
  twelve: "12",
  thirteen: "13",
  fourteen: "14",
  fifteen: "15",
  sixteen: "16",
  seventeen: "17",
  eighteen: "18",
  nineteen: "19",
  twenty: "20",
  thirty: "30",
  forty: "40",
  fifty: "50",
  sixty: "60",
  seventy: "70",
  eighty: "80",
  ninety: "90",
};

export function normalizeTranscriptDraft(
  raw: string,
  language: LanguageCode
): string {
  let text = raw.trim();
  if (!text) return text;

  text = text.replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
  text = text.replace(/\s+/g, " ");

  for (const [pattern, replacement] of SIMPLE_REPLACEMENTS) {
    text = text.replace(pattern, replacement);
  }

  if (language === "en" || language === "pcm") {
    text = text.replace(
      /\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)\b/gi,
      (match) => NUMBER_WORDS[match.toLowerCase()] ?? match
    );
  }

  text = text.replace(/\bghs\s+(\d)/gi, "GHS $1");
  text = text.replace(/\s+([,.!?])/g, "$1");

  if (!/[.!?]$/.test(text)) {
    return text;
  }

  return text;
}
