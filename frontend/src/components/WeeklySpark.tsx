"use client";
/**
 * WeeklySpark — SVG sparkline chart showing the last 7 days of net profit.
 * Handles positive and negative values with a dynamic baseline.
 * No external charting library required.
 */

import { shortDay, formatAmount } from "@/styles/theme";
import type { DayData } from "@/lib/types";

interface WeeklySparkProps {
  data: DayData[];
  currency?: string;
  height?: number;
}

const W = 280; // SVG coordinate width
const H = 64; // SVG coordinate height
const PADDING = { top: 8, bottom: 20, left: 4, right: 4 };

export default function WeeklySpark({
  data,
  currency = "GHS",
  height = 80,
}: WeeklySparkProps) {
  if (!data.length) {
    return (
      <div
        className="flex items-center justify-center bg-white rounded-2xl border border-border p-4"
        style={{ height }}
      >
        <p className="text-xs text-text-disabled">No data yet</p>
      </div>
    );
  }

  const profits = data.map((d) => d.profit);
  const maxProfit = Math.max(...profits, 1);
  const minProfit = Math.min(...profits, 0);
  const range = maxProfit - minProfit || 1;

  const plotW = W - PADDING.left - PADDING.right;
  const plotH = H - PADDING.top - PADDING.bottom;

  // Map data point → SVG coordinates
  const toX = (i: number) =>
    PADDING.left + (i / (data.length - 1)) * plotW;
  const toY = (val: number) =>
    PADDING.top + plotH - ((val - minProfit) / range) * plotH;

  // Baseline Y (where profit = 0)
  const baselineY = toY(0);

  // Build polyline points
  const points = data
    .map((d, i) => `${toX(i).toFixed(1)},${toY(d.profit).toFixed(1)}`)
    .join(" ");

  // Fill polygon: go across the line, down to baseline, back
  const fillPoints =
    points +
    ` ${toX(data.length - 1).toFixed(1)},${baselineY.toFixed(1)}` +
    ` ${toX(0).toFixed(1)},${baselineY.toFixed(1)}`;

  const allPositive = minProfit >= 0;
  const lineColor = allPositive ? "#1B5E20" : "#F57F17";
  const fillColor = allPositive
    ? "rgba(27,94,32,0.12)"
    : "rgba(245,127,23,0.12)";

  // Find today (last data point)
  const lastIdx = data.length - 1;
  const lastX = toX(lastIdx);
  const lastY = toY(data[lastIdx].profit);

  return (
    <div className="bg-white rounded-2xl border border-border shadow-card overflow-hidden">
      {/* Header row */}
      <div className="px-4 pt-3 pb-1 flex items-center justify-between">
        <span className="text-xs font-semibold text-text-secondary uppercase tracking-wide">
          7-Day Profit
        </span>
        <span
          className={`text-xs font-mono font-semibold ${
            data[lastIdx]?.profit >= 0 ? "text-primary-800" : "text-danger"
          }`}
        >
          {data[lastIdx]
            ? formatAmount(data[lastIdx].profit, currency)
            : "—"}
          <span className="text-text-disabled font-sans font-normal ml-1">
            today
          </span>
        </span>
      </div>

      {/* SVG sparkline */}
      <div className="px-3 pb-1">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          height={height - 36}
          preserveAspectRatio="none"
          aria-label="7-day profit sparkline"
        >
          {/* Baseline */}
          <line
            x1={PADDING.left}
            y1={baselineY}
            x2={W - PADDING.right}
            y2={baselineY}
            stroke="#E0E0E0"
            strokeWidth="1"
            strokeDasharray="4,3"
          />

          {/* Fill area */}
          <polygon points={fillPoints} fill={fillColor} />

          {/* Trend line */}
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Today dot */}
          <circle
            cx={lastX}
            cy={lastY}
            r="4"
            fill={lineColor}
            stroke="white"
            strokeWidth="1.5"
          />

          {/* Day labels */}
          {data.map((d, i) => (
            <text
              key={i}
              x={toX(i)}
              y={H - 4}
              textAnchor="middle"
              fontSize="8"
              fill="#9E9E9E"
            >
              {shortDay(d.date)}
            </text>
          ))}
        </svg>
      </div>
    </div>
  );
}
