"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api, Video } from "@/lib/api-client";
import { useJobPolling } from "@/hooks/useJobPolling";
import { BatchSubmitForm } from "@/components/job/BatchSubmitForm";

function formatDuration(seconds: number | null): string {
  if (!seconds) return "--:--";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    imported: "bg-gray-100 text-gray-700",
    scanning: "bg-amber-200 text-amber-950",
    scanned: "bg-blue-100 text-blue-700",
    reviewed: "bg-green-100 text-green-700",
    published: "bg-purple-100 text-purple-700",
  };
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || "bg-gray-100 text-gray-700"}`}>
      {status}
    </span>
  );
}

function VideoRow({
  video,
  onScan,
  onDelete,
  deleting,
}: {
  video: Video;
  onScan: (id: string) => void;
  onDelete: (id: string) => void;
  deleting: boolean;
}) {
  return (
    <div className="flex items-center justify-between p-4 bg-white border border-gray-200 rounded-lg">
      <div className="flex items-center gap-4 flex-1 min-w-0">
        {video.thumbnail_url && (
          <img src={video.thumbnail_url} alt="" className="w-24 h-14 object-cover rounded" />
        )}
        <div className="min-w-0">
          <Link href={`/videos/${video.id}`} className="font-medium text-gray-900 hover:text-blue-600 truncate block">
            {video.title}
          </Link>
          <div className="flex gap-3 mt-1 text-sm text-gray-500">
            <span>{video.channel_title}</span>
            <span>{formatDuration(video.duration_seconds)}</span>
          </div>
        </div>
      </div>
      <div className="flex items-center gap-3 ml-4">
        {video.compliance_score !== null && (
          <span className="text-sm font-medium text-gray-700">
            {Math.round(video.compliance_score)}%
          </span>
        )}
        <StatusBadge status={video.status} />
        <button
          onClick={() => onScan(video.id)}
          disabled={video.status === "scanning"}
          className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {video.status === "imported" ? "Scan" : "Rescan"}
        </button>
        <button
          onClick={() => onDelete(video.id)}
          disabled={deleting}
          className="px-3 py-1.5 text-sm border border-red-200 text-red-700 rounded hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {deleting ? "Deleting..." : "Delete"}
        </button>
      </div>
    </div>
  );
}

export default function VideosPage() {
  const searchParams = useSearchParams();
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showBatch, setShowBatch] = useState(false);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [lastJobSummary, setLastJobSummary] = useState<string | null>(null);
  const [lastJobFailed, setLastJobFailed] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const { job: activeJob } = useJobPolling(activeJobId);
  const importedId = searchParams.get("imported");

  const loadVideos = useCallback(async () => {
    try {
      setError(null);
      const data = await api.listVideos();
      let nextVideos = data.videos;

      // Import can succeed while list fetch is stale/intermittent; backfill the imported item explicitly.
      if (importedId && !data.videos.some((video) => video.id === importedId)) {
        try {
          const importedVideo = await api.getVideo(importedId);
          nextVideos = [importedVideo, ...data.videos];
        } catch (e) {
          setError(
            e instanceof Error
              ? `Imported video lookup failed: ${e.message}`
              : "Imported video lookup failed"
          );
        }
      }

      setVideos(nextVideos);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load videos");
    } finally {
      setLoading(false);
    }
  }, [importedId]);

  useEffect(() => {
    loadVideos();
  }, [loadVideos]);

  useEffect(() => {
    if (activeJob?.status === "completed" || activeJob?.status === "failed") {
      setLastJobSummary(activeJob.result_summary || activeJob.error_message || null);
      setLastJobFailed(activeJob.status === "failed");
      loadVideos();
      setActiveJobId(null);
    }
  }, [activeJob, loadVideos]);

  const handleScan = async (videoId: string) => {
    try {
      const job = await api.startScan(videoId);
      setLastJobSummary(null);
      setLastJobFailed(false);
      setActiveJobId(job.id);
      loadVideos();
    } catch {
      // ignore
    }
  };

  const handleDelete = async (videoId: string) => {
    const confirmed = window.confirm("Delete this video and all related scan/caption data?");
    if (!confirmed) return;

    setDeletingId(videoId);
    try {
      await api.deleteVideo(videoId);
      if (activeJob?.video_id === videoId) {
        setActiveJobId(null);
      }
      await loadVideos();
    } catch {
      // ignore
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-8">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Videos</h1>
          <div className="flex items-center gap-3">
            {videos.length > 0 && (
              <button
                onClick={() => setShowBatch(!showBatch)}
                className="text-sm px-3 py-1.5 border border-gray-300 rounded hover:bg-gray-50"
              >
                {showBatch ? "Hide Batch" : "Batch Scan"}
              </button>
            )}
            <Link href="/" className="text-blue-600 hover:text-blue-800 text-sm font-medium">
              + Import Video
            </Link>
          </div>
        </div>

        {activeJob && (
          <div className="mb-4 p-3 bg-amber-100 border border-amber-400 text-amber-950 rounded-lg text-sm">
            <span className="font-semibold">Scanning:</span>{" "}
            {activeJob.current_step || "Starting..."} — {activeJob.progress}%
          </div>
        )}
        {!activeJob && lastJobSummary && (
          <div className={`mb-4 p-3 border rounded-lg text-sm ${lastJobFailed ? "bg-red-50 border-red-200 text-red-700" : "bg-green-50 border-green-200 text-green-800"}`}>
            {lastJobSummary}
          </div>
        )}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {showBatch && (
          <div className="mb-6">
            <BatchSubmitForm
              videos={videos}
              onSubmitted={() => {
                loadVideos();
                setShowBatch(false);
              }}
            />
          </div>
        )}

        {loading ? (
          <p className="text-gray-500">Loading...</p>
        ) : videos.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <p>No videos imported yet.</p>
            <Link href="/" className="text-blue-600 hover:text-blue-800 mt-2 inline-block">
              Import your first video
            </Link>
          </div>
        ) : (
          <div className="space-y-3">
            {videos.map((video) => (
              <VideoRow
                key={video.id}
                video={video}
                onScan={handleScan}
                onDelete={handleDelete}
                deleting={deletingId === video.id}
              />
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
