import { useEditorStore } from "@/stores/editor-store";

export function FormatBadge() {
  const label = useEditorStore((s) => s.formatLabel);
  const color = useEditorStore((s) => s.formatColor);
  const description = useEditorStore((s) => s.formatDescription);

  return (
    <div className="flex items-center gap-2">
      <span
        className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold text-white"
        style={{ backgroundColor: color }}
      >
        {label}
      </span>
      {description && <span className="text-xs text-text-muted">{description}</span>}
    </div>
  );
}
