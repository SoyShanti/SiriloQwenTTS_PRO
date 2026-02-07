import { Play, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { ProgressBar } from "./ProgressBar";
import { AudioResult } from "./AudioResult";
import { useEditorStore } from "@/stores/editor-store";
import { useVoiceStore } from "@/stores/voice-store";
import { useStyleStore } from "@/stores/style-store";
import { useAppStore } from "@/stores/app-store";
import { useProductionStore } from "@/stores/production-store";
import { useSSEProgress } from "@/hooks/use-sse-progress";
import { startProduction } from "@/api/production";
import type { ProductionRequest } from "@/lib/types";

export function GenerateButton() {
  const content = useEditorStore((s) => s.content);
  const format = useEditorStore((s) => s.format);
  const selectedVoice = useVoiceStore((s) => s.selectedVoice);
  const speakerVoiceMap = useVoiceStore((s) => s.speakerVoiceMap);
  const computedInstruct = useStyleStore((s) => s.computedInstruct);
  const { language, modelVersion } = useAppStore();
  const { status, setJob, setFailed, reset } = useProductionStore();

  // Connect SSE when jobId is active
  useSSEProgress();

  const isRunning = status === "pending" || status === "running";

  const handleGenerate = async () => {
    if (!content.trim()) return;

    reset();

    // Parse selected voice
    let voiceName: string | undefined;
    let speaker: string | undefined;

    if (format !== "podcast_script" && selectedVoice) {
      if (selectedVoice.startsWith("qwen:")) {
        speaker = selectedVoice.replace("qwen:", "");
      } else if (selectedVoice.startsWith("clone:")) {
        voiceName = selectedVoice.replace("clone:", "");
      }
    }

    const req: ProductionRequest = {
      content,
      format,
      voice_name: voiceName,
      model_version: modelVersion,
      language,
      instruct: computedInstruct || undefined,
      speaker,
      speaker_voices: format === "podcast_script" ? speakerVoiceMap : undefined,
    };

    try {
      const { job_id } = await startProduction(req);
      setJob(job_id);
    } catch (e) {
      setFailed(e instanceof Error ? e.message : "Error al iniciar generacion");
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <Button
          className="w-full"
          size="lg"
          onClick={handleGenerate}
          disabled={isRunning || !content.trim()}
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Generando...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Generar audio
            </>
          )}
        </Button>
        <ProgressBar />
        <AudioResult />
      </CardContent>
    </Card>
  );
}
