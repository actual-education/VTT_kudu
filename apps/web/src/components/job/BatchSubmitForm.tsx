"use client";

import { useState } from "react";
import { api, Video } from "@/lib/api-client";

interface BatchSubmitFormProps {
  videos: Video[];
  onSubmitted: () => void;
}

export function BatchSubmitForm({ videos, onSubmitted }: BatchSubmitFormProps) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eligible = videos.filter((v) => v.status === "imported" || v.status === "scanned");

  const toggleAll = () => {
    if (selected.size === eligible.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(eligible.map((v) => v.id)));
    }
  };

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (selected.size === 0) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.startBatchScan(Array.from(selected));
      setSelected(new Set());
      onSubmitted();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Batch scan failed");
    } finally {
      setSubmitting(false);
    }
  };

  if (eligible.length === 0) {
    return (
      <div className="text-sm text-gray-400 py-4 text-center">
        No videos eligible for batch scan.
      </div>
    );
  }

  return (
    <div className="border border-gray-200 rounded-lg bg-white">
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={selected.size === eligible.length}
              onChange={toggleAll}
              className="rounded"
            />
            <span className="text-gray-600">
              Select all ({eligible.length})
            </span>
          </label>
        </div>
        <button
          onClick={handleSubmit}
          disabled={submitting || selected.size === 0}
          className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {submitting
            ? "Submitting..."
            : `Scan ${selected.size} video${selected.size !== 1 ? "s" : ""}`}
        </button>
      </div>

      {error && (
        <div className="px-4 py-2 text-sm text-red-600 bg-red-50">{error}</div>
      )}

      <div className="divide-y divide-gray-100 max-h-64 overflow-y-auto">
        {eligible.map((video) => (
          <label
            key={video.id}
            className="flex items-center gap-3 px-4 py-2 hover:bg-gray-50 cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.has(video.id)}
              onChange={() => toggle(video.id)}
              className="rounded"
            />
            <div className="min-w-0 flex-1">
              <div className="text-sm text-gray-900 truncate">{video.title}</div>
              <div className="text-xs text-gray-500">{video.status}</div>
            </div>
          </label>
        ))}
      </div>
    </div>
  );
}
