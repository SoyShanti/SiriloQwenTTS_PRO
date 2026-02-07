import { Progress } from "@/components/ui/progress";
import { useProductionStore } from "@/stores/production-store";

export function ProgressBar() {
  const { status, progress, message } = useProductionStore();

  if (status === "idle" || status === "completed") return null;

  return (
    <div className="space-y-2">
      <Progress value={progress * 100} />
      <div className="flex items-center justify-between text-xs text-text-muted">
        <span>{message}</span>
        <span>{Math.round(progress * 100)}%</span>
      </div>
      {status === "failed" && (
        <p className="text-xs text-danger">{message}</p>
      )}
    </div>
  );
}
