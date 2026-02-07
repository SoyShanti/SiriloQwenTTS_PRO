import { apiFetch } from "./client";
import { API_BASE } from "@/lib/constants";
import type { ProductionRequest, ProgressEvent } from "@/lib/types";

export function startProduction(req: ProductionRequest) {
  return apiFetch<{ job_id: string }>("/production/generate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export function connectSSE(
  jobId: string,
  onProgress: (event: ProgressEvent) => void,
  onError: (error: string) => void,
): () => void {
  const url = `${API_BASE}/production/progress/${jobId}`;
  const source = new EventSource(url);

  source.addEventListener("progress", (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ProgressEvent;
    onProgress(data);
    if (data.status === "completed" || data.status === "failed") {
      source.close();
    }
  });

  source.onerror = () => {
    onError("Connection lost");
    source.close();
  };

  return () => source.close();
}
