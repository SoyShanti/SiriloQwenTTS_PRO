import { Textarea } from "@/components/ui/textarea";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { FileUploader } from "./FileUploader";
import { FormatBadge } from "./FormatBadge";
import { useEditorStore } from "@/stores/editor-store";
import { useFormatDetection } from "@/hooks/use-format-detection";

export function UniversalEditor() {
  const content = useEditorStore((s) => s.content);
  const fileName = useEditorStore((s) => s.fileName);
  const setContent = useEditorStore((s) => s.setContent);

  // Triggers format detection on content change (debounced 500ms)
  useFormatDetection();

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Contenido</CardTitle>
          <FormatBadge />
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <FileUploader />
        {fileName && (
          <p className="text-xs text-text-muted">
            Archivo: <span className="text-text-secondary">{fileName}</span>
          </p>
        )}
        <Textarea
          placeholder="Escribe o pega tu texto aqui...&#10;&#10;Texto plano, script de podcast [MM:SS] Speaker: texto, o JSON de audiolibro"
          className="min-h-[200px] font-mono text-sm"
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />
        <p className="text-xs text-text-muted">
          {content.length > 0 ? `${content.length} caracteres` : "Sin contenido"}
        </p>
      </CardContent>
    </Card>
  );
}
