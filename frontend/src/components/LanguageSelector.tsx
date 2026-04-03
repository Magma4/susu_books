"use client";
/**
 * LanguageSelector — Dropdown to choose the interaction language.
 * Shows the native name of each language. Compact for the top bar.
 */

import { LANGUAGES, type LanguageCode } from "@/lib/types";

interface LanguageSelectorProps {
  value: LanguageCode;
  onChange: (code: LanguageCode) => void;
}

export default function LanguageSelector({
  value,
  onChange,
}: LanguageSelectorProps) {
  const current = LANGUAGES.find((l) => l.code === value) ?? LANGUAGES[0];

  return (
    <div className="relative flex items-center gap-1.5">
      {/* Globe icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4 text-text-secondary flex-shrink-0"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="2" y1="12" x2="22" y2="12" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>

      <select
        value={value}
        onChange={(e) => onChange(e.target.value as LanguageCode)}
        className="
          appearance-none bg-transparent pr-6 pl-0 py-1 text-sm font-medium
          text-text-primary border-none focus:outline-none focus:ring-2
          focus:ring-primary-light focus:ring-offset-1 rounded cursor-pointer
          hover:text-primary-900 transition-colors
        "
        aria-label="Select language"
      >
        {LANGUAGES.map((lang) => (
          <option key={lang.code} value={lang.code}>
            {lang.nativeName}
          </option>
        ))}
      </select>

      {/* Chevron */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="pointer-events-none absolute right-0 h-3 w-3 text-text-secondary"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </div>
  );
}
