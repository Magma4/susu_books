"use client";
/**
 * LoadingPulse — Three animated dots shown while the AI is processing.
 */

interface LoadingPulseProps {
  size?: "sm" | "md" | "lg";
  color?: "green" | "amber" | "white";
  label?: string;
}

const sizeMap = {
  sm: "h-1.5 w-1.5",
  md: "h-2.5 w-2.5",
  lg: "h-3.5 w-3.5",
};

const colorMap = {
  green: "bg-primary-800",
  amber: "bg-accent-800",
  white: "bg-white",
};

const delayMap = ["[animation-delay:-0.32s]", "[animation-delay:-0.16s]", ""];

export default function LoadingPulse({
  size = "md",
  color = "green",
  label = "Processing…",
}: LoadingPulseProps) {
  const dotClass = `${sizeMap[size]} ${colorMap[color]} rounded-full animate-bounce-dot`;

  return (
    <div
      className="flex items-center gap-1.5"
      role="status"
      aria-label={label}
    >
      {delayMap.map((delay, i) => (
        <span key={i} className={`${dotClass} ${delay}`} />
      ))}
      <span className="sr-only">{label}</span>
    </div>
  );
}
