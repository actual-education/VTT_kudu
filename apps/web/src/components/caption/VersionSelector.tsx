"use client";

import type { CaptionVersion } from "@/lib/api-client";

interface VersionSelectorProps {
  versions: CaptionVersion[];
  selectedId: string | null;
  onSelect: (version: CaptionVersion) => void;
}

const LABEL_STYLES: Record<string, string> = {
  raw_auto: "bg-gray-100 text-gray-600",
  enhanced: "bg-blue-100 text-blue-700",
  reviewed: "bg-purple-100 text-purple-700",
  published: "bg-green-100 text-green-700",
};

export function VersionSelector({ versions, selectedId, onSelect }: VersionSelectorProps) {
  if (versions.length === 0) return null;

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">Version:</span>
      <select
        value={selectedId || ""}
        onChange={(e) => {
          const v = versions.find((v) => v.id === e.target.value);
          if (v) onSelect(v);
        }}
        className="text-xs border border-gray-200 rounded px-2 py-1 bg-white"
      >
        {versions.map((v) => (
          <option key={v.id} value={v.id}>
            v{v.version_number} ({v.label})
          </option>
        ))}
      </select>
    </div>
  );
}
