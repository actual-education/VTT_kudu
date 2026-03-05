"use client";

const RISK_STYLES: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-green-100 text-green-800 border-green-200",
};

const RISK_LABELS: Record<string, string> = {
  VISUAL_TEXT_UNMENTIONED: "Text not mentioned",
  DIAGRAM_UNDESCRIBED: "Diagram undescribed",
  EQUATION_UNREAD: "Equation unread",
  CHART_UNDESCRIBED: "Chart undescribed",
  MODEL_UNCERTAIN: "Low confidence",
};

export function RiskBadge({
  level,
  reason,
}: {
  level: string | null;
  reason?: string | null;
}) {
  if (!level) return null;
  const style = RISK_STYLES[level] || RISK_STYLES.low;
  const reasonLabel = reason ? RISK_LABELS[reason] || reason : null;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {level}
      {reasonLabel && (
        <span className="text-[10px] opacity-75">({reasonLabel})</span>
      )}
    </span>
  );
}
