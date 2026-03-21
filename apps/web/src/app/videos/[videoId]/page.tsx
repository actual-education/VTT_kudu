"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import {
  api,
  Video,
  Segment,
  CaptionVersion,
  ComplianceBreakdown,
  Job,
} from "@/lib/api-client";
import { AppShell } from "@/components/layout/AppShell";
import { VideoPlayer } from "@/components/video/VideoPlayer";
import { CueTimeline } from "@/components/caption/CueTimeline";
import { CueList } from "@/components/caption/CueList";
import { CueEditor } from "@/components/caption/CueEditor";
import { VersionSelector } from "@/components/caption/VersionSelector";
import { ReviewPanel } from "@/components/review/ReviewPanel";
import { useCueSync } from "@/hooks/useCueSync";

export default function VideoDetailPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;

  const [video, setVideo] = useState<Video | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [versions, setVersions] = useState<CaptionVersion[]>([]);
  const [selectedVersion, setSelectedVersion] = useState<CaptionVersion | null>(null);
  const [compliance, setCompliance] = useState<ComplianceBreakdown | null>(null);
  const [latestJob, setLatestJob] = useState<Job | null>(null);
  const [latestSummaryJob, setLatestSummaryJob] = useState<Job | null>(null);
  const [editingSegment, setEditingSegment] = useState<Segment | null>(null);
  const [loading, setLoading] = useState(true);

  // Player state
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const playerRef = useRef<YT.Player | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const { activeSegmentId } = useCueSync(segments, currentTime);

  // Data loading
  const loadData = useCallback(async () => {
    try {
      const [v, segs, vers, comp, job, summaryJob] = await Promise.all([
        api.getVideo(videoId),
        api.listSegments(videoId),
        api.listCaptionVersions(videoId),
        api.getCompliance(videoId).catch(() => null),
        api.getLatestJobForVideo(videoId).catch(() => null),
        api.getLatestSummaryJobForVideo(videoId).catch(() => null),
      ]);
      setVideo(v);
      setSegments(segs);
      setVersions(vers);
      if (vers.length > 0) setSelectedVersion(vers[vers.length - 1]);
      setCompliance(comp);
      setLatestJob(job);
      setLatestSummaryJob(summaryJob);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const isRunning = latestJob?.status === "queued" || latestJob?.status === "running" || video?.status === "scanning";
    if (!isRunning) return;

    const timer = setInterval(() => {
      loadData();
    }, 3000);

    return () => clearInterval(timer);
  }, [latestJob?.status, loadData, video?.status]);

  // Player callbacks
  const handlePlayerReady = useCallback((player: YT.Player) => {
    playerRef.current = player;
    setDuration(player.getDuration());
  }, []);

  const handleStateChange = useCallback((event: YT.OnStateChangeEvent) => {
    if (event.data === YT.PlayerState.PLAYING) {
      intervalRef.current = setInterval(() => {
        if (playerRef.current?.getCurrentTime) {
          setCurrentTime(playerRef.current.getCurrentTime());
        }
      }, 250);
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, []);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const seekTo = useCallback((time: number) => {
    playerRef.current?.seekTo(time, true);
    setCurrentTime(time);
  }, []);

  // Segment actions
  const handleAccept = useCallback(
    async (segmentId: string) => {
      await api.updateSegment(videoId, segmentId, { review_status: "approved" });
      setSegments((prev) =>
        prev.map((s) => (s.id === segmentId ? { ...s, review_status: "approved" } : s))
      );
    },
    [videoId]
  );

  const handleReject = useCallback(
    async (segmentId: string) => {
      await api.updateSegment(videoId, segmentId, { review_status: "rejected" });
      setSegments((prev) =>
        prev.map((s) => (s.id === segmentId ? { ...s, review_status: "rejected" } : s))
      );
    },
    [videoId]
  );

  const handleEdit = useCallback(
    (segmentId: string) => {
      const seg = segments.find((s) => s.id === segmentId);
      if (seg) setEditingSegment(seg);
    },
    [segments]
  );

  const handleSaveCue = useCallback(
    async (segmentId: string, text: string) => {
      await api.updateSegment(videoId, segmentId, {
        transcript_text: text,
        review_status: "edited",
      });
      setSegments((prev) =>
        prev.map((s) =>
          s.id === segmentId ? { ...s, transcript_text: text, review_status: "edited" } : s
        )
      );
      setEditingSegment(null);
    },
    [videoId]
  );

  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [validationIssues, setValidationIssues] = useState<{ severity: string; message: string }[] | null>(null);
  const [rescanning, setRescanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<string | null>(null);

  const handleUpload = useCallback(async () => {
    setUploading(true);
    setUploadMsg(null);
    setValidationIssues(null);
    try {
      // Pre-upload validation
      const validation = await api.validateUpload(videoId);
      if (!validation.ready) {
        setValidationIssues(validation.issues);
        setUploading(false);
        return;
      }
      // Show warnings but proceed
      if (validation.issues.length > 0) {
        setValidationIssues(validation.issues);
      }
      const result = await api.uploadToYouTube(videoId);
      setUploadMsg(result.message);
      setVideo((prev) => prev ? { ...prev, status: "published" } : prev);
    } catch (e) {
      setUploadMsg(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }, [videoId]);

  const handleRescan = useCallback(async () => {
    setRescanning(true);
    setScanMsg(null);
    try {
      await api.startScan(videoId);
      setVideo((prev) => (prev ? { ...prev, status: "scanning" } : prev));
      setScanMsg("Rescan started. You can monitor progress on the Videos page.");
    } catch (e) {
      setScanMsg(e instanceof Error ? e.message : "Failed to start rescan");
    } finally {
      setRescanning(false);
    }
  }, [videoId]);

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64 text-gray-400">
          Loading...
        </div>
      </AppShell>
    );
  }

  if (!video) {
    return (
      <AppShell>
        <div className="flex items-center justify-center h-64 text-gray-400">
          Video not found
        </div>
      </AppShell>
    );
  }

  const isActiveScan = latestJob?.status === "queued" || latestJob?.status === "running";
  const summaryToShow = isActiveScan ? latestSummaryJob : latestJob;
  const summaryIsFailure = summaryToShow?.status === "failed";

  return (
    <AppShell>
      <div className="flex-1 flex overflow-hidden">
        {/* Left panel: Video + Timeline + Cue List */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-gray-200">
          {/* Video title + export bar */}
          <div className="px-4 py-3 border-b border-gray-200 bg-white">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <h1 className="text-lg font-semibold text-gray-900 truncate">
                  {video.title}
                </h1>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                  <span>{video.channel_title}</span>
                  {video.compliance_score !== null && (
                    <span className="font-medium">
                      Score: {Math.round(video.compliance_score)}%
                    </span>
                  )}
                  <span className="px-1.5 py-0.5 bg-gray-100 rounded">{video.status}</span>
                </div>
                {summaryToShow && (summaryToShow.status === "completed" || summaryToShow.status === "failed") && summaryToShow.result_summary && (
                  <p
                    className={`mt-2 text-xs px-2 py-1 rounded ${
                      summaryIsFailure
                        ? "text-red-700 bg-red-50"
                        : "text-green-700 bg-green-50"
                    }`}
                  >
                    {isActiveScan ? `Previous run: ${summaryToShow.result_summary}` : summaryToShow.result_summary}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={api.exportOriginalVttUrl(videoId)}
                  download
                  className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Original VTT
                </a>
                <a
                  href={api.exportVisualDescriptionsVttUrl(videoId)}
                  download
                  className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Description VTT
                </a>
                <a
                  href={api.exportReportUrl(videoId)}
                  download
                  className="px-3 py-1.5 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                >
                  Download Report
                </a>
                <button
                  onClick={handleRescan}
                  disabled={rescanning || video.status === "scanning"}
                  className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {rescanning ? "Starting..." : "Rescan"}
                </button>
                <button
                  onClick={handleUpload}
                  disabled={uploading}
                  className="px-3 py-1.5 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                >
                  {uploading ? "Uploading..." : "Upload to YouTube"}
                </button>
              </div>
            </div>
            {scanMsg && (
              <p className="mt-2 text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded">
                {scanMsg}
              </p>
            )}
            {uploadMsg && (
              <p className="mt-2 text-xs text-green-700 bg-green-50 px-2 py-1 rounded">
                {uploadMsg}
              </p>
            )}
            {validationIssues && validationIssues.length > 0 && (
              <div className="mt-2 space-y-1">
                {validationIssues.map((issue, i) => (
                  <p
                    key={i}
                    className={`text-xs px-2 py-1 rounded ${
                      issue.severity === "critical"
                        ? "text-red-700 bg-red-50"
                        : "text-yellow-700 bg-yellow-50"
                    }`}
                  >
                    {issue.severity === "critical" ? "BLOCKED: " : "Warning: "}
                    {issue.message}
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Video player */}
          <div className="px-4 pt-4">
            <VideoPlayer
              youtubeId={video.youtube_id}
              onReady={handlePlayerReady}
              onStateChange={handleStateChange}
            />
          </div>

          {/* Timeline */}
          <div className="px-4 py-3">
            <CueTimeline
              segments={segments}
              duration={duration}
              currentTime={currentTime}
              activeSegmentId={activeSegmentId}
              onSeek={seekTo}
            />
          </div>

          {/* Cue editor (when active) */}
          {editingSegment && (
            <div className="px-4 pb-3">
              <CueEditor
                segment={editingSegment}
                onSave={handleSaveCue}
                onClose={() => setEditingSegment(null)}
              />
            </div>
          )}

          {/* Caption version selector + Cue list */}
          <div className="px-4 pb-2 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-600">
              Segments ({segments.length})
            </span>
            <VersionSelector
              versions={versions}
              selectedId={selectedVersion?.id ?? null}
              onSelect={setSelectedVersion}
            />
          </div>

          <div className="flex-1 overflow-y-auto px-4 pb-4">
            <CueList
              segments={segments}
              activeSegmentId={activeSegmentId}
              onSelect={(seg) => setEditingSegment(seg)}
              onSeek={seekTo}
            />
          </div>
        </div>

        {/* Right panel: Review */}
        <div className="w-96 shrink-0 bg-white overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-900">Review Panel</h2>
          </div>
          <div className="flex-1 overflow-hidden">
            <ReviewPanel
              segments={segments}
              compliance={compliance}
              onAccept={handleAccept}
              onReject={handleReject}
              onEdit={handleEdit}
              onSeek={seekTo}
            />
          </div>
        </div>
      </div>
    </AppShell>
  );
}
