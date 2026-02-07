import { useEffect, useRef } from "react";
import { useEditorStore } from "@/stores/editor-store";
import { detectContent } from "@/api/content";

export function useFormatDetection() {
  const content = useEditorStore((s) => s.content);
  const setFormat = useEditorStore((s) => s.setFormat);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);

    if (!content.trim()) {
      setFormat("plain_text", "Texto plano", "", "#4A90D9", []);
      return;
    }

    timerRef.current = setTimeout(async () => {
      try {
        const result = await detectContent(content);
        setFormat(result.format, result.label, result.description, result.color, result.speakers);
      } catch {
        // Silently fail — keep current format
      }
    }, 500);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [content, setFormat]);
}
