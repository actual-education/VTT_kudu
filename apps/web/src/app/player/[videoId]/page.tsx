"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api, type Segment, type Video } from "@/lib/api-client";
import { VideoPlayer } from "@/components/video/VideoPlayer";
import { VisualDescriptionOverlay } from "@/components/video/VisualDescriptionOverlay";
import { PlayerControls } from "@/components/video/PlayerControls";
import {
  useVisualDescriptionSync,
  type VisualDescriptionMode,
} from "@/hooks/useVisualDescriptionSync";
import { usePauseOnCue } from "@/hooks/usePauseOnCue";

export default function InteractivePlayerPage() {
  const params = useParams<{ videoId: string }>();
  const videoId = params.videoId;

  const [video, setVideo] = useState<Video | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [descriptionsEnabled, setDescriptionsEnabled] = useState(true);
  const [overlayEnabled, setOverlayEnabled] = useState(true);
  const [sidePanelEnabled, setSidePanelEnabled] = useState(true);
  const [mode, setMode] = useState<Exclude<VisualDescriptionMode, "OFF">>("EDUCATIONAL");
  const [pauseEnabled, setPauseEnabled] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const playerRef = useRef<YT.Player | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const effectiveMode: VisualDescriptionMode = descriptionsEnabled ? mode : "OFF";
  const { cues, activeCue } = useVisualDescriptionSync(segments, currentTime, effectiveMode);

  const clearTracking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const startTracking = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = setInterval(() => {
      if (playerRef.current?.getCurrentTime) {
        setCurrentTime(playerRef.current.getCurrentTime());
      }
    }, 250);
  }, []);

  usePauseOnCue({
    cue: activeCue,
    enabled: descriptionsEnabled && pauseEnabled,
    player: playerRef.current,
  });

  useEffect(() => {
    const loadData = async () => {
      try {
        const [loadedVideo, loadedSegments] = await Promise.all([
          api.getVideo(videoId),
          api.listSegments(videoId),
        ]);
        setVideo(loadedVideo);
        setSegments(loadedSegments);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : "Failed to load player");
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [videoId]);

  useEffect(() => clearTracking, [clearTracking]);

  const handleReady = useCallback((player: YT.Player) => {
    playerRef.current = player;
  }, []);

  const handleStateChange = useCallback(
    (event: YT.OnStateChangeEvent) => {
      if (event.data === YT.PlayerState.PLAYING) {
        setIsPlaying(true);
        startTracking();
        return;
      }

      setIsPlaying(false);
      clearTracking();

      if (
        event.data === YT.PlayerState.PAUSED ||
        event.data === YT.PlayerState.ENDED ||
        event.data === YT.PlayerState.CUED
      ) {
        setCurrentTime(event.target.getCurrentTime());
      }
    },
    [clearTracking, startTracking]
  );

  if (loading) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e0f2fe_0%,#f8fafc_45%,#e2e8f0_100%)] px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-6xl rounded-[2rem] border border-white/70 bg-white/70 p-8 shadow-xl backdrop-blur">
          Loading player...
        </div>
      </main>
    );
  }

  if (!video) {
    return (
      <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e0f2fe_0%,#f8fafc_45%,#e2e8f0_100%)] px-6 py-10 text-slate-900">
        <div className="mx-auto max-w-6xl rounded-[2rem] border border-white/70 bg-white/70 p-8 shadow-xl backdrop-blur">
          <p className="text-lg font-semibold">Video not found</p>
          {error && <p className="mt-2 text-sm text-rose-700">{error}</p>}
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,#e0f2fe_0%,#f8fafc_45%,#e2e8f0_100%)] px-4 py-6 text-slate-900 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="rounded-[2rem] border border-white/70 bg-white/72 p-4 shadow-xl backdrop-blur sm:p-6">
          <div className="flex flex-col gap-4 border-b border-slate-200/80 pb-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-800">
                Accessible viewing mode
              </p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">
                {video.title}
              </h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-600">
                Visual descriptions are synced from processed AVCE segments and can be filtered or auto-paused for comprehension.
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              <Link
                href={`/videos/${videoId}`}
                className="rounded-full border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:border-slate-400 hover:bg-slate-50"
              >
                Back to review
              </Link>
              <Link
                href="/videos"
                className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                All videos
              </Link>
            </div>
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
            <section className="space-y-5">
              <div className="relative overflow-hidden rounded-[1.75rem] border border-slate-900/10 bg-slate-950 shadow-2xl">
                <VideoPlayer
                  youtubeId={video.youtube_id}
                  onReady={handleReady}
                  onStateChange={handleStateChange}
                  className="rounded-none"
                />
                <VisualDescriptionOverlay
                  cue={activeCue}
                  visible={descriptionsEnabled && overlayEnabled && effectiveMode !== "OFF"}
                />
              </div>

              {error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                  {error}
                </div>
              )}

              <PlayerControls
                descriptionsEnabled={descriptionsEnabled}
                overlayEnabled={overlayEnabled}
                sidePanelEnabled={sidePanelEnabled}
                mode={mode}
                pauseEnabled={pauseEnabled}
                cueCount={cues.length}
                onDescriptionsEnabledChange={(enabled) => {
                  setDescriptionsEnabled(enabled);
                  if (!enabled) {
                    setPauseEnabled(false);
                    setOverlayEnabled(false);
                    setSidePanelEnabled(false);
                    return;
                  }
                  setOverlayEnabled(true);
                  setSidePanelEnabled(true);
                }}
                onOverlayEnabledChange={setOverlayEnabled}
                onSidePanelEnabledChange={setSidePanelEnabled}
                onModeChange={setMode}
                onPauseEnabledChange={setPauseEnabled}
              />
            </section>

            <aside className="rounded-3xl border border-slate-200 bg-white/90 p-5 shadow-sm">
              <h2 className="text-sm font-semibold text-slate-900">Current description</h2>
              <p className="mt-1 text-sm text-slate-500">
                The description panel updates from the segment timeline while the video plays.
              </p>

              <div className="mt-5 rounded-2xl bg-slate-950 px-4 py-5 text-slate-50">
                {descriptionsEnabled && sidePanelEnabled && activeCue ? (
                  <>
                    <p className="text-[0.65rem] font-semibold uppercase tracking-[0.24em] text-sky-300">
                      {activeCue.educationLevel ?? "low"} educational priority
                    </p>
                    <p className="mt-3 text-sm leading-6 text-slate-100">
                      {activeCue.description}
                    </p>
                  </>
                ) : descriptionsEnabled && !sidePanelEnabled ? (
                  <p className="text-sm leading-6 text-slate-300">
                    Right-column display is turned off. Enable it in Viewing controls to show active descriptions here.
                  </p>
                ) : !descriptionsEnabled ? (
                  <p className="text-sm leading-6 text-slate-300">
                    Visual descriptions are off.
                  </p>
                ) : (
                  <p className="text-sm leading-6 text-slate-300">
                    No active description at the current playback position.
                  </p>
                )}
              </div>

              <div className="mt-5 grid gap-3 text-sm text-slate-600">
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Filter mode
                  </span>
                  <span className="mt-1 block text-slate-900">
                    {descriptionsEnabled ? mode : "OFF"}
                  </span>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Video overlay
                  </span>
                  <span className="mt-1 block text-slate-900">
                    {descriptionsEnabled && overlayEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Right column
                  </span>
                  <span className="mt-1 block text-slate-900">
                    {descriptionsEnabled && sidePanelEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
                <div className="rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="block text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Pause on cue
                  </span>
                  <span className="mt-1 block text-slate-900">
                    {descriptionsEnabled && pauseEnabled ? "Enabled" : "Disabled"}
                  </span>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </div>
    </main>
  );
}
