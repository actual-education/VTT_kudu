"use client";

import type { ComplianceBreakdown } from "@/lib/api-client";

function ScoreRing({ score, size = 80 }: { score: number; size?: number }) {
  const radius = (size - 8) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color =
    score >= 80 ? "text-green-500" : score >= 50 ? "text-yellow-500" : "text-red-500";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90" width={size} height={size}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          className="text-gray-200"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={color}
        />
      </svg>
      <span className="absolute text-sm font-bold text-gray-900">
        {Math.round(score)}%
      </span>
    </div>
  );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  const color =
    score >= 80 ? "bg-green-400" : score >= 50 ? "bg-yellow-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-28 text-gray-600 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div
          className={`h-2 rounded-full ${color}`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <span className="w-8 text-right text-gray-700 font-medium">{Math.round(score)}</span>
    </div>
  );
}

export function ComplianceScore({ data }: { data: ComplianceBreakdown | null }) {
  if (!data) return <div className="text-gray-400 text-sm">No compliance data</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4">
        <ScoreRing score={data.overall_score} />
        <div>
          <div className="text-sm font-medium text-gray-900">Overall Score</div>
          <div className="text-xs text-gray-500">
            {data.total_segments} segments analyzed
          </div>
          <div className="flex gap-2 mt-1 text-xs">
            <span className="text-red-600">{data.high_risk_count} high</span>
            <span className="text-yellow-600">{data.medium_risk_count} med</span>
            <span className="text-green-600">{data.low_risk_count} low</span>
          </div>
        </div>
      </div>
      <div className="space-y-2">
        <ScoreBar label="Captions" score={data.caption_completeness} />
        <ScoreBar label="Visual coverage" score={data.visual_coverage} />
        <ScoreBar label="Manual review" score={data.manual_review} />
        <ScoreBar label="Confidence" score={data.model_uncertainty} />
        <ScoreBar label="OCR reliability" score={data.ocr_reliability} />
      </div>
    </div>
  );
}
