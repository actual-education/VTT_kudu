"use client";

import { useMemo } from "react";
import type { Segment } from "@/lib/api-client";

export function useCueSync(segments: Segment[], currentTime: number) {
  const activeSegmentId = useMemo(() => {
    const active = segments.find(
      (s) => currentTime >= s.start_time && currentTime < s.end_time
    );
    return active?.id ?? null;
  }, [segments, currentTime]);

  const activeSegment = useMemo(() => {
    return segments.find((s) => s.id === activeSegmentId) ?? null;
  }, [segments, activeSegmentId]);

  return { activeSegmentId, activeSegment };
}
