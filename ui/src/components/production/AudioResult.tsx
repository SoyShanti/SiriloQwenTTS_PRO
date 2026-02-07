import { AudioPlayer } from "@/components/audio/AudioPlayer";
import { useProductionStore } from "@/stores/production-store";

export function AudioResult() {
  const { status, audioUrl } = useProductionStore();

  if (status !== "completed" || !audioUrl) return null;

  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-success">Audio generado</label>
      <AudioPlayer src={audioUrl} />
    </div>
  );
}
