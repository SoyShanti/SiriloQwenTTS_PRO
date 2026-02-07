import { useStyleStore } from "@/stores/style-store";

const ICON_MAP: Record<string, string> = {
  mic: "🎙️",
  drama: "🎭",
  chat: "💬",
  cloud: "☁️",
  flame: "🔥",
  ear: "👂",
  megaphone: "📢",
  brain: "🧠",
  smile: "😄",
  eye: "👁️",
};

export function ModalitySelector() {
  const { modalities, selectedModality, setSelectedModality } = useStyleStore();

  if (modalities.length === 0) return null;

  return (
    <div className="space-y-2">
      <label className="text-xs font-medium text-text-muted">Quick Modality</label>
      <div className="flex flex-wrap gap-2">
        {modalities.map((m) => (
          <button
            key={m.name}
            onClick={() =>
              setSelectedModality(selectedModality === m.name ? null : m.name)
            }
            className={`flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs transition-colors ${
              selectedModality === m.name
                ? "border-brand bg-brand/10 text-brand"
                : "border-border bg-surface-secondary text-text-secondary hover:border-text-muted"
            }`}
            title={m.description}
          >
            <span>{ICON_MAP[m.icon] ?? "🎵"}</span>
            <span>{m.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
