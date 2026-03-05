"use client";

import { useState } from "react";
import type { Segment, ComplianceBreakdown } from "@/lib/api-client";
import { ComplianceScore } from "./ComplianceScore";
import { SuggestionCard } from "./SuggestionCard";

interface ReviewPanelProps {
  segments: Segment[];
  compliance: ComplianceBreakdown | null;
  onAccept: (segmentId: string) => void;
  onReject: (segmentId: string) => void;
  onEdit: (segmentId: string) => void;
  onSeek: (time: number) => void;
}

type RiskFilter = "all" | "high" | "medium" | "low";

export function ReviewPanel({
  segments,
  compliance,
  onAccept,
  onReject,
  onEdit,
  onSeek,
}: ReviewPanelProps) {
  const [filter, setFilter] = useState<RiskFilter>("all");

  const flaggedSegments = segments.filter((s) => s.ai_suggestion);
  const filtered =
    filter === "all"
      ? flaggedSegments
      : flaggedSegments.filter((s) => s.risk_level === filter);

  const counts = {
    all: flaggedSegments.length,
    high: flaggedSegments.filter((s) => s.risk_level === "high").length,
    medium: flaggedSegments.filter((s) => s.risk_level === "medium").length,
    low: flaggedSegments.filter((s) => s.risk_level === "low").length,
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <ComplianceScore data={compliance} />
      </div>

      <div className="p-3 border-b border-gray-200">
        <div className="flex gap-1">
          {(["all", "high", "medium", "low"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-2 py-1 rounded text-xs font-medium ${
                filter === f
                  ? "bg-blue-100 text-blue-700"
                  : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {f === "all" ? "All" : f.charAt(0).toUpperCase() + f.slice(1)} ({counts[f]})
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {filtered.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-8">
            No flagged segments
          </p>
        ) : (
          filtered.map((seg) => (
            <div
              key={seg.id}
              onClick={() => onSeek(seg.start_time)}
              className="cursor-pointer"
            >
              <SuggestionCard
                segment={seg}
                onAccept={onAccept}
                onReject={onReject}
                onEdit={onEdit}
              />
            </div>
          ))
        )}
      </div>
    </div>
  );
}
