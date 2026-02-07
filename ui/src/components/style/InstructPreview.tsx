import { useStyleStore } from "@/stores/style-store";

export function InstructPreview() {
  const instruct = useStyleStore((s) => s.computedInstruct);

  if (!instruct) return null;

  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-text-muted">Generated instruct</label>
      <div className="rounded-md bg-surface-active border border-border p-3 text-xs text-text-secondary font-mono whitespace-pre-wrap">
        {instruct}
      </div>
    </div>
  );
}
