"use client";

export const CURRENCIES = [
  { code: "GHS", name: "Cedi", symbol: "₵" },
  { code: "NGN", name: "Naira", symbol: "₦" },
  { code: "KES", name: "Shilling", symbol: "KSh" },
  { code: "USD", name: "Dollar", symbol: "$" },
  { code: "EUR", name: "Euro", symbol: "€" },
  { code: "GBP", name: "Pound", symbol: "£" },
  { code: "INR", name: "Rupee", symbol: "₹" },
  { code: "CNY", name: "Yuan", symbol: "¥" },
  { code: "JPY", name: "Yen", symbol: "¥" },
  { code: "AED", name: "Dirham", symbol: "د.إ" },
  { code: "RUB", name: "Ruble", symbol: "₽" },
];

interface CurrencySelectorProps {
  value: string;
  onChange: (code: string) => void;
}

export default function CurrencySelector({
  value,
  onChange,
}: CurrencySelectorProps) {
  return (
    <div className="relative flex items-center gap-1">
      {/* Coin Icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4 text-text-secondary flex-shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>

      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="
          appearance-none bg-transparent pr-4 pl-0 py-1 text-sm font-medium
          text-text-primary border-none focus:outline-none focus:ring-2
          focus:ring-primary-light focus:ring-offset-1 rounded cursor-pointer
          hover:text-primary-900 transition-colors
        "
        aria-label="Select currency"
      >
        {CURRENCIES.map((c) => (
          <option key={c.code} value={c.code}>
            {c.code}
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
