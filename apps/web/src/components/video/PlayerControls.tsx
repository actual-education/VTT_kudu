"use client";

import type { VisualDescriptionMode } from "@/hooks/useVisualDescriptionSync";

interface PlayerControlsProps {
  descriptionsEnabled: boolean;
  overlayEnabled: boolean;
  sidePanelEnabled: boolean;
  mode: Exclude<VisualDescriptionMode, "OFF">;
  pauseEnabled: boolean;
  cueCount: number;
  onDescriptionsEnabledChange: (enabled: boolean) => void;
  onOverlayEnabledChange: (enabled: boolean) => void;
  onSidePanelEnabledChange: (enabled: boolean) => void;
  onModeChange: (mode: Exclude<VisualDescriptionMode, "OFF">) => void;
  onPauseEnabledChange: (enabled: boolean) => void;
}

export function PlayerControls({
  descriptionsEnabled,
  overlayEnabled,
  sidePanelEnabled,
  mode,
  pauseEnabled,
  cueCount,
  onDescriptionsEnabledChange,
  onOverlayEnabledChange,
  onSidePanelEnabledChange,
  onModeChange,
  onPauseEnabledChange,
}: PlayerControlsProps) {
  return (
    <section className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Viewing controls</h2>
          <p className="mt-1 text-sm text-slate-600">
            {cueCount} synced visual description{cueCount === 1 ? "" : "s"} available
          </p>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          Interactive mode
        </span>
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Visual descriptions
            </span>
            <span className="block text-xs text-slate-500">
              Master switch for filtered visual description cues
            </span>
          </span>
          <input
            type="checkbox"
            checked={descriptionsEnabled}
            onChange={(event) => onDescriptionsEnabledChange(event.target.checked)}
            className="h-4 w-4 accent-slate-900"
          />
        </label>

        <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Video overlay
            </span>
            <span className="block text-xs text-slate-500">
              Render the active description directly on the player
            </span>
          </span>
          <input
            type="checkbox"
            checked={overlayEnabled}
            onChange={(event) => onOverlayEnabledChange(event.target.checked)}
            disabled={!descriptionsEnabled}
            className="h-4 w-4 accent-slate-900"
          />
        </label>

        <label className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <span className="block text-sm font-medium text-slate-900">Level</span>
          <span className="mt-1 block text-xs text-slate-500">
            Educational keeps only high educational-priority cues
          </span>
          <select
            value={mode}
            onChange={(event) =>
              onModeChange(event.target.value as Exclude<VisualDescriptionMode, "OFF">)
            }
            disabled={!descriptionsEnabled}
            className="mt-3 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <option value="ALL">All</option>
            <option value="EDUCATIONAL">Educational</option>
          </select>
        </label>

        <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Right column
            </span>
            <span className="block text-xs text-slate-500">
              Keep the current description visible in the side panel
            </span>
          </span>
          <input
            type="checkbox"
            checked={sidePanelEnabled}
            onChange={(event) => onSidePanelEnabledChange(event.target.checked)}
            disabled={!descriptionsEnabled}
            className="h-4 w-4 accent-slate-900"
          />
        </label>

        <label className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
          <span>
            <span className="block text-sm font-medium text-slate-900">
              Pause mode
            </span>
            <span className="block text-xs text-slate-500">
              Pause for 5 seconds when a new description appears
            </span>
          </span>
          <input
            type="checkbox"
            checked={pauseEnabled}
            onChange={(event) => onPauseEnabledChange(event.target.checked)}
            disabled={!descriptionsEnabled}
            className="h-4 w-4 accent-slate-900"
          />
        </label>
      </div>
    </section>
  );
}
