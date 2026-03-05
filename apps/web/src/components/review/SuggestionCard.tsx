"use client";

import type { Segment } from "@/lib/api-client";
import { RiskBadge } from "./RiskBadge";

interface SuggestionCardProps {
  segment: Segment;
  onAccept: (segmentId: string) => void;
  onReject: (segmentId: string) => void;
  onEdit: (segmentId: string) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function SuggestionCard({ segment, onAccept, onReject, onEdit }: SuggestionCardProps) {
  if (!segment.ai_suggestion) return null;

  const isReviewed = segment.review_status === "approved" || segment.review_status === "rejected";

  return (
    <div className={`border rounded-lg p-3 text-sm ${isReviewed ? "opacity-60" : "border-blue-200 bg-blue-50"}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-gray-500">
          {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
        </span>
        <RiskBadge level={segment.risk_level} reason={segment.risk_reason} />
      </div>

      {segment.transcript_text && (
        <p className="text-gray-700 mb-2 text-xs italic">
          &quot;{segment.transcript_text}&quot;
        </p>
      )}

      <div className="bg-white border border-blue-100 rounded p-2 mb-2">
        <div className="text-[10px] uppercase tracking-wide text-blue-600 font-medium mb-1">
          AI Suggestion
        </div>
        <p className="text-gray-800">{segment.ai_suggestion}</p>
      </div>

      {!isReviewed && (
        <div className="flex gap-2">
          <button
            onClick={() => onAccept(segment.id)}
            className="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
          >
            Accept
          </button>
          <button
            onClick={() => onEdit(segment.id)}
            className="px-3 py-1 bg-gray-200 text-gray-700 rounded text-xs hover:bg-gray-300"
          >
            Edit
          </button>
          <button
            onClick={() => onReject(segment.id)}
            className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200"
          >
            Reject
          </button>
        </div>
      )}

      {isReviewed && (
        <div className="text-xs text-gray-500">
          Status: <span className="font-medium">{segment.review_status}</span>
        </div>
      )}
    </div>
  );
}
