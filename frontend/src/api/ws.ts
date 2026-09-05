import { useEffect, useRef, useState } from "react";
import { wsUrl } from "./client";
import { getJob } from "./jobs";
import type { Job, ProgressFrame } from "../types/job";

const POLL_INTERVAL_MS = 3000;

/**
 * Follows a job's progress via WebSocket, falling back to polling GET
 * /api/jobs/{id} if the socket drops - the MVP's resilience story for a
 * single-host deployment rather than a reconnect protocol.
 */
export function useJobProgress(jobId: string | undefined) {
  const [job, setJob] = useState<Job | null>(null);
  const [latestFrame, setLatestFrame] = useState<ProgressFrame | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;

    getJob(jobId).then((j) => !cancelled && setJob(j));

    const stopPolling = () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };

    const startPolling = () => {
      if (pollRef.current) return;
      pollRef.current = setInterval(async () => {
        const j = await getJob(jobId);
        if (cancelled) return;
        setJob(j);
        if (["completed", "failed", "cancelled"].includes(j.status)) stopPolling();
      }, POLL_INTERVAL_MS);
    };

    const ws = new WebSocket(wsUrl(`/api/jobs/${jobId}/progress`));
    ws.onmessage = (event) => {
      if (cancelled) return;
      const frame: ProgressFrame = JSON.parse(event.data);
      setLatestFrame(frame);
      if (frame.terminal) {
        getJob(jobId).then((j) => !cancelled && setJob(j));
      }
    };
    ws.onerror = () => startPolling();
    ws.onclose = () => startPolling();

    return () => {
      cancelled = true;
      ws.close();
      stopPolling();
    };
  }, [jobId]);

  return { job, latestFrame };
}
