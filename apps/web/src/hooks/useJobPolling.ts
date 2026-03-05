"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { api, Job } from "@/lib/api-client";

export function useJobPolling(jobId: string | null, intervalMs = 2000) {
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const poll = useCallback(async () => {
    if (!jobId) return;
    try {
      const data = await api.getJob(jobId);
      setJob(data);
      if (data.status === "completed" || data.status === "failed") {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Polling failed");
    }
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    poll();
    intervalRef.current = setInterval(poll, intervalMs);
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [jobId, intervalMs, poll]);

  return { job, error };
}
