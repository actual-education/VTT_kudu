"use client";

import { useEffect, useRef, useCallback } from "react";

interface VideoPlayerProps {
  youtubeId: string;
  onReady?: (player: YT.Player) => void;
  onStateChange?: (event: YT.OnStateChangeEvent) => void;
  className?: string;
}

let apiLoaded = false;
let apiLoading = false;
const readyCallbacks: (() => void)[] = [];

function loadYouTubeAPI(): Promise<void> {
  if (apiLoaded) return Promise.resolve();
  return new Promise((resolve) => {
    if (apiLoading) {
      readyCallbacks.push(resolve);
      return;
    }
    apiLoading = true;
    readyCallbacks.push(resolve);

    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);

    window.onYouTubeIframeAPIReady = () => {
      apiLoaded = true;
      readyCallbacks.forEach((cb) => cb());
      readyCallbacks.length = 0;
    };
  });
}

export function VideoPlayer({
  youtubeId,
  onReady,
  onStateChange,
  className,
}: VideoPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<YT.Player | null>(null);

  const initPlayer = useCallback(async () => {
    await loadYouTubeAPI();
    if (!containerRef.current || playerRef.current) return;

    const div = document.createElement("div");
    containerRef.current.innerHTML = "";
    containerRef.current.appendChild(div);

    playerRef.current = new YT.Player(div, {
      videoId: youtubeId,
      width: "100%",
      height: "100%",
      playerVars: {
        autoplay: 0,
        modestbranding: 1,
        rel: 0,
        cc_load_policy: 0,
      },
      events: {
        onReady: (event: YT.PlayerEvent) => onReady?.(event.target),
        onStateChange,
      },
    });
  }, [youtubeId, onReady, onStateChange]);

  useEffect(() => {
    initPlayer();
    return () => {
      playerRef.current?.destroy();
      playerRef.current = null;
    };
  }, [initPlayer]);

  return (
    <div
      ref={containerRef}
      className={`w-full aspect-video bg-black rounded-lg overflow-hidden ${
        className ?? ""
      }`}
    />
  );
}
