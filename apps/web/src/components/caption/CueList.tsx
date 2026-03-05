"use client";

import { useEffect, useRef } from "react";
import type { Segment } from "@/lib/api-client";
import { RiskBadge } from "../review/RiskBadge";

interface CueListProps {
  segments: Segment[];
  activeSegmentId: string | null;
  onSelect: (segment: Segment) => void;
  onSeek: (time: number) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function CueList({ segments, activeSegmentId, onSelect, onSeek }: CueListProps) {
  const activeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [activeSegmentId]);

  return (
    <div className="overflow-y-auto space-y-1">
      {segments.map((seg) => {
        const isActive = seg.id === activeSegmentId;
        return (
          <div
            key={seg.id}
            ref={isActive ? activeRef : undefined}
            onClick={() => {
              onSelect(seg);
              onSeek(seg.start_time);
            }}
            className={`p-2 rounded text-sm cursor-pointer border transition-colors ${
              isActive
                ? "bg-blue-50 border-blue-300"
                : "bg-white border-gray-100 hover:border-gray-200"
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-gray-400 font-mono">
                {formatTime(seg.start_time)}
              </span>
              <div className="flex items-center gap-1">
                {seg.ai_suggestion && (
                  <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" title="Has AI suggestion" />
                )}
                <RiskBadge level={seg.risk_level} />
              </div>
            </div>
            <p className="text-gray-700 text-xs leading-relaxed line-clamp-2">
              {seg.transcript_text || "(no transcript)"}
            </p>
          </div>
        );
      })}
    </div>
  );
}
