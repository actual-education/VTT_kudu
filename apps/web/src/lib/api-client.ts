const API_BASE = "/api";

function normalizeErrorDetail(detail: unknown): string {
  if (typeof detail === "string" && detail.trim()) return detail;

  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const msg = (item as { msg?: unknown }).msg;
          return typeof msg === "string" ? msg : JSON.stringify(item);
        }
        return JSON.stringify(item);
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join("; ");
  }

  if (detail && typeof detail === "object") {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === "string" && message.trim()) return message;
    return JSON.stringify(detail);
  }

  return "";
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = normalizeErrorDetail(error?.detail);
    throw new Error(detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return undefined as T;
  }

  return res.json();
}

async function requestText(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.text();
}

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
  status: string;
  created_at: string;
  updated_at: string;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
}

export interface Job {
  id: string;
  video_id: string;
  status: string;
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
  education_level: "low" | "high" | null;
  risk_reason: string | null;
  review_status: string;
}

export interface CaptionVersion {
  id: string;
  video_id: string;
  version_number: number;
  label: string;
  vtt_content: string;
  created_at: string;
}

export interface ComplianceBreakdown {
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
}

export interface AuthStatus {
  authenticated: boolean;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  login: (password: string) =>
    request<AuthStatus>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
    }),

  logout: () =>
    request<AuthStatus>("/auth/logout", {
      method: "POST",
    }),

  me: () => request<AuthStatus>("/auth/me"),

  importVideo: (url: string) =>
    request<Video>("/videos", {
      method: "POST",
      body: JSON.stringify({ url }),
    }),

  listVideos: () =>
    request<VideoListResponse>("/videos", {
      cache: "no-store",
    }),

  getVideo: (id: string) => request<Video>(`/videos/${id}`),

  deleteVideo: (id: string) =>
    request<void>(`/videos/${id}`, {
      method: "DELETE",
    }),

  startScan: (videoId: string) =>
    request<Job>("/jobs/scan", {
      method: "POST",
      body: JSON.stringify({ video_id: videoId }),
    }),

  startBatchScan: (videoIds: string[]) =>
    request<Job[]>("/jobs/batch", {
      method: "POST",
      body: JSON.stringify({ video_ids: videoIds }),
    }),

  getJob: (jobId: string) => request<Job>(`/jobs/${jobId}`),

  getLatestJobForVideo: (videoId: string) =>
    request<Job | null>(`/jobs/videos/${videoId}/latest`),

  getLatestSummaryJobForVideo: (videoId: string) =>
    request<Job | null>(`/jobs/videos/${videoId}/latest-summary`),

  // Segments
  listSegments: (videoId: string, riskLevel?: string) => {
    const params = riskLevel ? `?risk_level=${riskLevel}` : "";
    return request<Segment[]>(`/videos/${videoId}/segments${params}`);
  },

  updateSegment: (videoId: string, segmentId: string, data: Partial<Pick<Segment, "review_status" | "transcript_text" | "ai_suggestion">>) =>
    request<Segment>(`/videos/${videoId}/segments/${segmentId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  // Captions
  getLatestVtt: (videoId: string) => requestText(`/videos/${videoId}/captions/latest`),

  listCaptionVersions: (videoId: string) =>
    request<CaptionVersion[]>(`/videos/${videoId}/captions/versions`),

  // Compliance
  getCompliance: (videoId: string) =>
    request<ComplianceBreakdown>(`/videos/${videoId}/compliance`),

  // Export
  exportVttUrl: (videoId: string) => `${API_BASE}/videos/${videoId}/export/vtt`,
  exportOriginalVttUrl: (videoId: string) => `${API_BASE}/videos/${videoId}/export/vtt/original`,
  exportVisualDescriptionsVttUrl: (videoId: string) => `${API_BASE}/videos/${videoId}/export/vtt/descriptions`,
  exportHighEducationVisualDescriptionsVttUrl: (videoId: string) =>
    `${API_BASE}/videos/${videoId}/export/vtt/descriptions/high`,
  exportReportUrl: (videoId: string) => `${API_BASE}/videos/${videoId}/export/report`,

  validateUpload: (videoId: string) =>
    request<{
      ready: boolean;
      issues: { severity: string; message: string }[];
      total_segments: number;
      reviewed_count: number;
    }>(`/videos/${videoId}/export/validate`),

  uploadToYouTube: (videoId: string) =>
    request<{ status: string; message: string; youtube_id: string }>(
      `/videos/${videoId}/export/upload`,
      { method: "POST" }
    ),
};
