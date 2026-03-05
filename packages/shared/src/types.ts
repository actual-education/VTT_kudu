export interface Video {
  id: string;
  youtube_id: string;
  title: string;
  channel_title: string | null;
  duration_seconds: number | null;
  thumbnail_url: string | null;
  description: string | null;
  published_at: string | null;
  compliance_score: number | null;
  status: "imported" | "scanning" | "scanned" | "reviewed" | "published";
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  video_id: string;
  status: "queued" | "running" | "completed" | "failed";
  current_step: string | null;
  progress: number;
  error_message: string | null;
  result_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface Segment {
  id: string;
  video_id: string;
  start_time: number;
  end_time: number;
  transcript_text: string | null;
  ocr_text: string | null;
  visual_description: string | null;
  ai_suggestion: string | null;
  has_text: boolean;
  has_diagram: boolean;
  has_equation: boolean;
  risk_level: "low" | "medium" | "high" | null;
  risk_reason: string | null;
  review_status: "pending" | "approved" | "rejected" | "edited";
}

export interface FrameAnalysis {
  id: string;
  video_id: string;
  timestamp: number;
  has_text: boolean;
  has_diagram: boolean;
  has_equation: boolean;
  likely_essential: boolean;
  ocr_text: string | null;
  description: string | null;
  confidence: number | null;
}

export interface CaptionVersion {
  id: string;
  video_id: string;
  version_number: number;
  label: "raw_auto" | "enhanced" | "reviewed" | "published";
  vtt_content: string;
  created_at: string;
}

export interface VttCue {
  id?: string;
  startTime: number;
  endTime: number;
  text: string;
}

export interface ComplianceReport {
  video_id: string;
  title: string;
  overall_score: number;
  caption_completeness: number;
  visual_coverage: number;
  manual_review: number;
  model_uncertainty: number;
  ocr_reliability: number;
  total_segments: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  disclaimer: string;
}
