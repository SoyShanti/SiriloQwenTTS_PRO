import { useEffect, useCallback } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useStyleStore } from "@/stores/style-store";
import { buildInstruct } from "@/api/emotions";

export function StyleControls() {
  const {
    preset, emotion, emotionLevel, style, pace, intensity, customInstruct,
    emotions, emotionDetails, styles, paces, intensities, intensityLevels,
    setEmotion, setEmotionLevel, setStyle, setPace, setIntensity, setCustomInstruct, setComputedInstruct,
  } = useStyleStore();

  const isCustom = preset === "(custom)";

  const rebuild = useCallback(async () => {
    if (!isCustom) return;
    try {
      const res = await buildInstruct({
        emotion, style, pace, intensity, emotion_level: emotionLevel, custom: customInstruct, add_variation: true,
      });
      setComputedInstruct(res.instruct);
    } catch {
      // silent
    }
  }, [emotion, emotionLevel, style, pace, intensity, customInstruct, isCustom, setComputedInstruct]);

  useEffect(() => {
    rebuild();
  }, [rebuild]);

  if (!isCustom) return null;

  // Get emotion description for the current level
  const emotionHint = emotion !== "neutral" && emotionDetails[emotion]
    ? emotionDetails[emotion][emotionLevel as "low" | "mid" | "high"]
    : null;

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-text-muted">Emotion</label>
          <Select value={emotion} onValueChange={setEmotion}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {emotions.map((e) => (
                <SelectItem key={e} value={e}>{e}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-text-muted">Emotion Level</label>
          <Select value={emotionLevel} onValueChange={setEmotionLevel}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {intensityLevels.map((l) => (
                <SelectItem key={l} value={l}>{l}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          {emotionHint && (
            <p className="text-[10px] text-text-muted italic">{emotionHint}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-text-muted">Style</label>
          <Select value={style} onValueChange={setStyle}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {styles.map((s) => (
                <SelectItem key={s} value={s}>{s}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-text-muted">Pace</label>
          <Select value={pace} onValueChange={setPace}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {paces.map((p) => (
                <SelectItem key={p} value={p}>{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5 col-span-2">
          <label className="text-xs font-medium text-text-muted">Voice Intensity</label>
          <Select value={intensity} onValueChange={setIntensity}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {intensities.map((i) => (
                <SelectItem key={i} value={i}>{i}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="text-xs font-medium text-text-muted">Custom instruction</label>
        <Textarea
          placeholder="Add custom instructions..."
          className="min-h-[60px] text-xs"
          value={customInstruct}
          onChange={(e) => setCustomInstruct(e.target.value)}
        />
      </div>
    </div>
  );
}
