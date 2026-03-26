"use client";

import type { VisualDescriptionCue } from "@/hooks/useVisualDescriptionSync";

interface VisualDescriptionOverlayProps {
  cue: VisualDescriptionCue | null;
  visible: boolean;
}

const toneClasses: Record<string, string> = {
  high: "border-emerald-300/70 bg-emerald-50/92 text-emerald-950",
  medium: "border-sky-300/60 bg-sky-50/92 text-sky-950",
  low: "border-slate-300/60 bg-white/92 text-slate-950",
  null: "border-slate-300/60 bg-white/92 text-slate-950",
};

export function VisualDescriptionOverlay({
  cue,
  visible,
}: VisualDescriptionOverlayProps) {
  if (!cue || !visible) return null;

  const tone = toneClasses[String(cue.educationLevel)] ?? toneClasses.null;

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 p-4 sm:p-6">
      <div
        className={`mx-auto max-w-3xl rounded-2xl border px-4 py-3 shadow-lg backdrop-blur-sm sm:px-5 sm:py-4 ${tone}`}
      >
        <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] opacity-70">
          Visual
        </p>
        <p className="mt-1 text-base leading-6 font-medium sm:text-lg sm:leading-7">
          {cue.description}
        </p>
      </div>
    </div>
  );
}
