import { useEffect } from "react";
import { useProductionStore } from "@/stores/production-store";
import { connectSSE } from "@/api/production";

export function useSSEProgress() {
  const jobId = useProductionStore((s) => s.jobId);
  const status = useProductionStore((s) => s.status);
  const setProgress = useProductionStore((s) => s.setProgress);
  const setCompleted = useProductionStore((s) => s.setCompleted);
  const setFailed = useProductionStore((s) => s.setFailed);

  useEffect(() => {
    if (!jobId || status === "completed" || status === "failed" || status === "idle") return;

    const close = connectSSE(
      jobId,
      (event) => {
        if (event.status === "completed" && event.audio_url) {
          setCompleted(event.audio_url);
        } else if (event.status === "failed") {
          setFailed(event.error ?? event.message);
        } else {
          setProgress(event.status, event.progress, event.message);
        }
      },
      (error) => setFailed(error),
    );

    return close;
  }, [jobId, status, setProgress, setCompleted, setFailed]);
}
