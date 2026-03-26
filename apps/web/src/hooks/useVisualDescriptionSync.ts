"use client";

import { useMemo } from "react";
import type { Segment } from "@/lib/api-client";

export type VisualDescriptionMode = "ALL" | "EDUCATIONAL" | "OFF";

export interface VisualDescriptionCue {
  id: string;
  startTime: number;
  endTime: number;
  description: string;
  riskLevel: Segment["risk_level"];
  educationLevel: Segment["education_level"];
}

const DISPLAY_DELAY_SECONDS = 5;
const MERGE_GAP_SECONDS = 0.25;

function isEffectiveHighEducation(segment: Segment) {
  if (segment.education_level === "high") return true;

  const text = (segment.visual_description ?? "").trim().toLowerCase();
  if (!text) return false;

  const strongKeywords = [
    "educational graphic",
    "diagram",
    "equation",
    "formula",
    "graph",
    "chart",
    "field",
    "charge",
    "capacitor",
    "conductor",
    "cross-section",
    "labeled",
    "label",
    "arrow",
    "plate",
    "surface",
    "+q",
    "-q",
  ];

  const fillerMarkers = [
    "studio",
    "shelves",
    "green background",
    "green wall",
    "light bulbs",
    "decorative",
    "presenter speaking",
    "speaking directly to the camera",
    "presenter stands",
    "presenter sits",
    "person speaking directly",
  ];

  const strongMatch = strongKeywords.some((keyword) => text.includes(keyword));
  const fillerOnly = fillerMarkers.some((marker) => text.includes(marker)) && !strongMatch;

  return strongMatch && !fillerOnly;
}

function hasDescription(segment: Segment) {
  return Boolean(segment.visual_description?.trim());
}

function matchesMode(mode: VisualDescriptionMode, segment: Segment) {
  if (mode === "OFF") return false;
  if (mode === "ALL") return true;
  return isEffectiveHighEducation(segment);
}

export function useVisualDescriptionSync(
  segments: Segment[],
  currentTime: number,
  mode: VisualDescriptionMode
) {
  const cues = useMemo<VisualDescriptionCue[]>(() => {
    const rawCues = segments
      .filter((segment) => hasDescription(segment) && matchesMode(mode, segment))
      .map((segment) => ({
        id: segment.id,
        startTime: segment.start_time + DISPLAY_DELAY_SECONDS,
        endTime: segment.end_time,
        description: segment.visual_description?.trim() ?? "",
        riskLevel: segment.risk_level,
        educationLevel: segment.education_level,
      }));

    const merged: VisualDescriptionCue[] = [];
    for (const cue of rawCues) {
      const previous = merged[merged.length - 1];
      if (
        previous &&
        previous.description === cue.description &&
        previous.educationLevel === cue.educationLevel &&
        cue.startTime - previous.endTime <= MERGE_GAP_SECONDS
      ) {
        previous.endTime = Math.max(previous.endTime, cue.endTime);
        continue;
      }
      merged.push({ ...cue });
    }

    return merged;
  }, [mode, segments]);

  const activeCue = useMemo(() => {
    return (
      cues.find((cue) => currentTime >= cue.startTime && currentTime < cue.endTime) ?? null
    );
  }, [cues, currentTime]);

  return { cues, activeCue };
}
