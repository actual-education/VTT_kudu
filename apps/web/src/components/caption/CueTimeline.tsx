"use client";

import type { Segment } from "@/lib/api-client";

interface CueTimelineProps {
  segments: Segment[];
  duration: number;
  currentTime: number;
  activeSegmentId: string | null;
  onSeek: (time: number) => void;
}

const RISK_COLORS: Record<string, string> = {
  high: "bg-red-500",
  medium: "bg-yellow-400",
  low: "bg-green-400",
};

export function CueTimeline({
  segments,
  duration,
  currentTime,
  activeSegmentId,
  onSeek,
}: CueTimelineProps) {
  if (duration <= 0) return null;

  const playheadPct = (currentTime / duration) * 100;

  return (
    <div className="relative w-full">
      {/* Track */}
      <div
        className="relative h-8 bg-gray-100 rounded cursor-pointer"
        onClick={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const pct = (e.clientX - rect.left) / rect.width;
          onSeek(pct * duration);
        }}
      >
        {/* Segment markers */}
        {segments.map((seg) => {
          const left = (seg.start_time / duration) * 100;
          const width = ((seg.end_time - seg.start_time) / duration) * 100;
          const color = RISK_COLORS[seg.risk_level || "low"] || "bg-gray-300";
          const isActive = seg.id === activeSegmentId;

          return (
            <div
              key={seg.id}
              className={`absolute top-1 h-6 rounded-sm ${color} ${
                isActive ? "ring-2 ring-blue-500 ring-offset-1" : ""
              } hover:brightness-110 transition-all`}
              style={{ left: `${left}%`, width: `${Math.max(width, 0.3)}%` }}
              title={`${seg.risk_level || "unknown"}: ${seg.transcript_text?.slice(0, 50) || ""}`}
            />
          );
        })}

        {/* Playhead */}
        <div
          className="absolute top-0 w-0.5 h-full bg-blue-600 z-10 pointer-events-none"
          style={{ left: `${playheadPct}%` }}
        >
          <div className="absolute -top-1 -left-1 w-2.5 h-2.5 bg-blue-600 rounded-full" />
        </div>
      </div>

      {/* Time labels */}
      <div className="flex justify-between mt-1 text-[10px] text-gray-400">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}
