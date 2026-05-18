import type { LanguageCode } from "./types";

const SIMPLE_REPLACEMENTS: Array<[RegExp, string]> = [
  [/\bghana cedi(s)?\b/gi, "GHS"],
  [/\bcedi(s)?\b/gi, "GHS"],
  [/\bghana\b/gi, "GHS"],
  [/\bfrancs?\s+cfa\b/gi, "XOF"],
  [/\bcfa\b/gi, "XOF"],
  [/\beuros?\b/gi, "EUR"],
  [/\bd[oó]lares?\b/gi, "USD"],
  [/\bdollars?\b/gi, "USD"],
  [/\bkilos?\b/gi, "kg"],
  [/\bkilograms?\b/gi, "kg"],
  [/\bkilogrammes?\b/gi, "kg"],
  [/\bquilogramas?\b/gi, "kg"],
  [/\bkgs\b/gi, "kg"],
  [/\blitres?\b/gi, "liters"],
  [/\blitros?\b/gi, "liters"],
  [/\bltrs?\b/gi, "liters"],
  [/\bpalmoil\b/gi, "palm oil"],
  [/\bplantains\b/gi, "plantains"],
];

const NUMBER_WORDS_BY_LANGUAGE: Partial<Record<LanguageCode, Record<string, string>>> = {
  en: {
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
  },
  pcm: {
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
  },
  fr: {
    zéro: "0",
    zero: "0",
    un: "1",
    une: "1",
    deux: "2",
    trois: "3",
    quatre: "4",
    cinq: "5",
    six: "6",
    sept: "7",
    huit: "8",
    neuf: "9",
    dix: "10",
    onze: "11",
    douze: "12",
    treize: "13",
    quatorze: "14",
    quinze: "15",
    seize: "16",
    vingt: "20",
    trente: "30",
    quarante: "40",
    cinquante: "50",
    soixante: "60",
  },
  es: {
    cero: "0",
    uno: "1",
    una: "1",
    dos: "2",
    tres: "3",
    cuatro: "4",
    cinco: "5",
    seis: "6",
    siete: "7",
    ocho: "8",
    nueve: "9",
    diez: "10",
    once: "11",
    doce: "12",
    trece: "13",
    catorce: "14",
    quince: "15",
    veinte: "20",
    treinta: "30",
    cuarenta: "40",
    cincuenta: "50",
    sesenta: "60",
  },
  pt: {
    zero: "0",
    um: "1",
    uma: "1",
    dois: "2",
    duas: "2",
    três: "3",
    tres: "3",
    quatro: "4",
    cinco: "5",
    seis: "6",
    sete: "7",
    oito: "8",
    nove: "9",
    dez: "10",
    onze: "11",
    doze: "12",
    treze: "13",
    catorze: "14",
    quatorze: "14",
    quinze: "15",
    vinte: "20",
    trinta: "30",
    quarenta: "40",
    cinquenta: "50",
    sessenta: "60",
  },
};

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

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

  const numberWords = NUMBER_WORDS_BY_LANGUAGE[language];
  if (numberWords) {
    const pattern = new RegExp(
      `\\b(${Object.keys(numberWords).map(escapeRegExp).join("|")})\\b`,
      "gi"
    );
    text = text.replace(
      pattern,
      (match) => numberWords[match.toLowerCase()] ?? match
    );
  }

  text = text.replace(/\bghs\s+(\d)/gi, "GHS $1");
  text = text.replace(/\s+([,.!?])/g, "$1");

  if (!/[.!?]$/.test(text)) {
    return text;
  }

  return text;
}
