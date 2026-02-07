import { useCallback } from "react";
import { Upload } from "lucide-react";
import { useEditorStore } from "@/stores/editor-store";

export function FileUploader() {
  const setContent = useEditorStore((s) => s.setContent);
  const setFileName = useEditorStore((s) => s.setFileName);

  const handleFile = useCallback(
    async (file: File) => {
      const text = await file.text();
      setContent(text);
      setFileName(file.name);
    },
    [setContent, setFileName],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file && (file.name.endsWith(".txt") || file.name.endsWith(".json"))) {
        handleFile(file);
      }
    },
    [handleFile],
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile],
  );

  return (
    <label
      className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-border rounded-lg p-4 cursor-pointer hover:border-brand/50 hover:bg-surface-hover transition-colors"
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
    >
      <Upload className="h-5 w-5 text-text-muted" />
      <span className="text-xs text-text-muted">Arrastra .txt o .json, o haz click</span>
      <input type="file" accept=".txt,.json" className="hidden" onChange={handleChange} />
    </label>
  );
}
