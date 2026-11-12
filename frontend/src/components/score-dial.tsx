// Circular score dial (pure SVG — no chart library needed for one arc).
// Colour tiers follow the backend report's semantics: green ≥75, amber ≥50,
// red below 50 (pdf_export_service.py uses the same three tiers).

export function scoreTier(score: number): "high" | "mid" | "low" {
  if (score >= 75) return "high";
  if (score >= 50) return "mid";
  return "low";
}

const tierStroke = {
  high: "stroke-emerald-500",
  mid: "stroke-amber-500",
  low: "stroke-red-500",
};

const tierText = {
  high: "text-emerald-600",
  mid: "text-amber-600",
  low: "text-red-600",
};

export function ScoreDial({
  score,
  size = 160,
  label = "Overall match",
}: {
  score: number;
  size?: number;
  label?: string;
}) {
  const strokeWidth = 12;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const tier = scoreTier(clamped);

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`${label}: ${Math.round(clamped)} percent`}
    >
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          className="stroke-muted"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className={`${tierStroke[tier]} transition-all duration-700`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-4xl font-bold ${tierText[tier]}`}>
          {Math.round(clamped)}
          <span className="text-xl">%</span>
        </span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
    </div>
  );
}
