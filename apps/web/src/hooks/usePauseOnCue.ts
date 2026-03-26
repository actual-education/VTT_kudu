"use client";

import { useEffect, useRef } from "react";
import type { VisualDescriptionCue } from "./useVisualDescriptionSync";

interface UsePauseOnCueOptions {
  cue: VisualDescriptionCue | null;
  enabled: boolean;
  player: YT.Player | null;
  delayMs?: number;
}

export function usePauseOnCue({
  cue,
  enabled,
  player,
  delayMs = 5000,
}: UsePauseOnCueOptions) {
  const pausedCueIdRef = useRef<string | null>(null);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const previousCueIdRef = useRef<string | null>(null);

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!enabled || !cue) {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
        timeoutRef.current = null;
      }
      pausedCueIdRef.current = null;
      previousCueIdRef.current = cue?.id ?? null;
      return;
    }

    const isNewCue = previousCueIdRef.current !== cue.id;
    previousCueIdRef.current = cue.id;

    if (!isNewCue || pausedCueIdRef.current === cue.id) {
      return;
    }

    if (!player) {
      return;
    }

    if (player.getPlayerState() !== YT.PlayerState.PLAYING) {
      return;
    }

    pausedCueIdRef.current = cue.id;
    player.pauseVideo();

    timeoutRef.current = setTimeout(() => {
      timeoutRef.current = null;
      if (!player || !cue) return;
      if (player.getPlayerState() !== YT.PlayerState.PAUSED) return;
      if (pausedCueIdRef.current !== cue.id) return;
      player.playVideo();
    }, delayMs);
  }, [cue, delayMs, enabled, player]);
}
