import { useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { PresetSelector } from "./PresetSelector";
import { ModalitySelector } from "./ModalitySelector";
import { StyleControls } from "./StyleControls";
import { InstructPreview } from "./InstructPreview";
import { useStyleStore } from "@/stores/style-store";
import { fetchEmotions } from "@/api/emotions";

export function StylePanel() {
  const setOptions = useStyleStore((s) => s.setOptions);

  // Load emotion/style options on mount
  useEffect(() => {
    fetchEmotions()
      .then((data) =>
        setOptions({
          emotions: data.emotions,
          emotionDetails: data.emotion_details,
          styles: data.styles,
          paces: data.paces,
          intensities: data.intensities,
          intensityLevels: data.intensity_levels,
          presets: data.presets,
          modalities: data.modalities,
        })
      )
      .catch(() => {});
  }, [setOptions]);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Voice Style</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <ModalitySelector />
        <PresetSelector />
        <StyleControls />
        <InstructPreview />
      </CardContent>
    </Card>
  );
}
