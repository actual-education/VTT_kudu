"use client";

import { useState, useCallback, useRef, useEffect } from "react";

declare global {
  interface Window {
    YT: typeof YT;
    onYouTubeIframeAPIReady: (() => void) | undefined;
  }
}

export function useVideoPlayer(youtubeId: string) {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const playerRef = useRef<YT.Player | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const startTimeTracking = useCallback(() => {
    if (intervalRef.current) return;
    intervalRef.current = setInterval(() => {
      if (playerRef.current?.getCurrentTime) {
        setCurrentTime(playerRef.current.getCurrentTime());
      }
    }, 250);
  }, []);

  const stopTimeTracking = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const seekTo = useCallback((time: number) => {
    playerRef.current?.seekTo(time, true);
    setCurrentTime(time);
  }, []);

  const play = useCallback(() => {
    playerRef.current?.playVideo();
  }, []);

  const pause = useCallback(() => {
    playerRef.current?.pauseVideo();
  }, []);

  useEffect(() => {
    return () => stopTimeTracking();
  }, [stopTimeTracking]);

  const onPlayerReady = useCallback((event: YT.PlayerEvent) => {
    setDuration(event.target.getDuration());
    setIsReady(true);
  }, []);

  const onPlayerStateChange = useCallback(
    (event: YT.OnStateChangeEvent) => {
      if (event.data === YT.PlayerState.PLAYING) {
        setIsPlaying(true);
        startTimeTracking();
      } else {
        setIsPlaying(false);
        stopTimeTracking();
      }
    },
    [startTimeTracking, stopTimeTracking]
  );

  return {
    playerRef,
    currentTime,
    duration,
    isPlaying,
    isReady,
    seekTo,
    play,
    pause,
    onPlayerReady,
    onPlayerStateChange,
  };
}
