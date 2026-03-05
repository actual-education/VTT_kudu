"use client";

import { useState, useEffect } from "react";
import type { Segment } from "@/lib/api-client";
import { RiskBadge } from "../review/RiskBadge";

interface CueEditorProps {
  segment: Segment | null;
  onSave: (segmentId: string, text: string) => void;
  onClose: () => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function CueEditor({ segment, onSave, onClose }: CueEditorProps) {
  const [text, setText] = useState("");

  useEffect(() => {
    setText(segment?.transcript_text || "");
  }, [segment]);

  if (!segment) return null;

  return (
    <div className="border border-gray-200 rounded-lg bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-400">
            {formatTime(segment.start_time)} - {formatTime(segment.end_time)}
          </span>
          <RiskBadge level={segment.risk_level} reason={segment.risk_reason} />
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-sm"
        >
          Close
        </button>
      </div>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={3}
        className="w-full border border-gray-200 rounded p-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none"
      />

      {segment.ai_suggestion && (
        <div className="bg-blue-50 border border-blue-100 rounded p-2 text-xs">
          <span className="font-medium text-blue-700">AI suggestion: </span>
          <span className="text-gray-700">{segment.ai_suggestion}</span>
          <button
            onClick={() => setText((prev) => `${prev}\n${segment.ai_suggestion}`)}
            className="ml-2 text-blue-600 hover:text-blue-800 underline"
          >
            Insert
          </button>
        </div>
      )}

      {segment.ocr_text && (
        <div className="bg-gray-50 border border-gray-100 rounded p-2 text-xs">
          <span className="font-medium text-gray-600">OCR text: </span>
          <span className="text-gray-700">{segment.ocr_text}</span>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => onSave(segment.id, text)}
          className="px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
        >
          Save
        </button>
        <button
          onClick={onClose}
          className="px-3 py-1.5 bg-gray-100 text-gray-600 rounded text-sm hover:bg-gray-200"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
